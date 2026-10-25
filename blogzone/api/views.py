from rest_framework import viewsets, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from ..models import Post, Comment, Like, ViewEvent
from .serializers import PostSerializer
from django.shortcuts import get_object_or_404
from .serializers import PostSerializer, CommentSerializer, CommentCreateSerializer, CommentUpdateSerializer, DailyViewsSerializer
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAdminUser, SAFE_METHODS
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_date



# ====================================================================================


class CanManagePostsAPI(permissions.BasePermission):
    """
    Allow only Admin, Editor, Author, or superuser to create/edit posts.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.groups.filter(name__in=["Admin", "Editor", "Author"]).exists()

# ====================================================================================
class IsOwnerOrEditorOrAdmin(permissions.BasePermission):
    """
    Object-level: allow edit if user is superuser, Admin, Editor, or the post's author.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.groups.filter(name__in=["Admin", "Editor"]).exists():
            return True

        return obj.author_id == user.id
# ====================================================================================

class CanEditOrDeleteComment(permissions.BasePermission):
    """
    Only the comment author or Admin/Editor/staff can edit/delete.
    """

    def has_object_permission(self, request, view, obj):
        # Safe methods (GET, HEAD, OPTIONS) are allowed for everyone
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Admins / Editors / staff can edit/delete anything
        if user.is_superuser or user.is_staff or user.groups.filter(
            name__in=["Admin", "Editor"]
        ).exists():
            return True

        # Otherwise only the comment's author
        return obj.user_id == user.id

# ========================================================================================

class PostViewSet(viewsets.ModelViewSet):
    """
    API for blog posts.

    - GET list / retrieve: only published posts (public).
    - POST: create post (Author/Editor/Admin).
    - PUT/PATCH/DELETE: update post (owner or Editor/Admin).
    """
    lookup_field = "slug"

    def get_queryset(self):
        qs = (
            Post.objects
            .filter(status=Post.STATUS_PUBLISHED)
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count(
                    "comments",
                    filter=Q(comments__status=Comment.STATUS_APPROVED),
                    distinct=True,
                ),
            )
            .select_related("author", "category")
            .prefetch_related("tags")
            .order_by("-published_at")
        )
        return qs

    def get_serializer_class(self):
        # Use write serializer for create/update, read serializer for list/detail
        from .serializers import PostWriteSerializer
        if self.action in ["create", "update", "partial_update"]:
            return PostWriteSerializer
        return PostSerializer

    def get_permissions(self):
        # Write actions require auth + proper group + (for updates) owner/editor/admin
        if self.action in ["create", "update", "partial_update", "destroy"]:
            perms = [permissions.IsAuthenticated(), CanManagePostsAPI()]
            if self.action in ["update", "partial_update", "destroy"]:
                perms.append(IsOwnerOrEditorOrAdmin())
            return perms

        # list / retrieve are public
        return [permissions.AllowAny()]

# =============================================================================================
class DailyViewsPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 365

# ==============================================================================================
class PostCommentListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  -> list approved comments for a post
    POST -> create a new comment (pending moderation)
    """
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CommentCreateSerializer
        return CommentSerializer

    def get_post(self):
        slug = self.kwargs.get("slug")
        return get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)

    def get_queryset(self):
        post = self.get_post()
        return (
            Comment.objects
            .filter(post=post, status=Comment.STATUS_APPROVED)
            .select_related("user")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        """
        Create a pending comment for this post.
        Only allowed for authenticated users.
        """
        request = self.request
        if not request.user.is_authenticated:
            raise permissions.PermissionDenied("You must be logged in to comment.")

        post = self.get_post()
        parent_id = serializer.validated_data.get("parent_id")

        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, post=post)
            except Comment.DoesNotExist:
                parent = None

        Comment.objects.create(
            post=post,
            user=request.user,
            parent=parent,
            content=serializer.validated_data["content"],
            status=Comment.STATUS_PENDING,
        )
# ====================================================================================

class CommentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/comments/<id>/      -> single comment (mostly for debugging)
    PATCH  /api/comments/<id>/      -> update content (author or moderator only)
    DELETE /api/comments/<id>/      -> delete comment (author or moderator only)
    """
    queryset = Comment.objects.select_related("user", "post")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanEditOrDeleteComment]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return CommentUpdateSerializer
        return CommentSerializer

# =======================================================================================


class PostLikeToggleAPIView(APIView):
    """
    POST -> toggle like/unlike for the current user on a given post.
    Returns { liked: bool, likes_count: int }.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)

        like, created = Like.objects.get_or_create(post=post, user=request.user)

        if created:
            liked = True
        else:
            # Already liked => unlike
            like.delete()
            liked = False

        likes_count = Like.objects.filter(post=post).count()

        return Response(
            {"liked": liked, "likes_count": likes_count}
        )

# =========================================================================================
class PostStatsAPIView(APIView):
    """
    GET -> stats for a single post:
    views, likes, comments, edit_count, self/external views.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        post = get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)

        total_views = post.view_count or 0
        likes_count = Like.objects.filter(post=post).count()
        comments_count = Comment.objects.filter(
            post=post,
            status=Comment.STATUS_APPROVED,
        ).count()
        self_views = ViewEvent.objects.filter(
            post=post,
            user=post.author,
        ).count()
        external_views = total_views - self_views if total_views else 0

        data = {
            "post_id": post.id,
            "slug": post.slug,
            "title": post.title,
            "author": post.author.username if post.author_id else None,
            "view_count": total_views,
            "self_views": self_views,
            "external_views": external_views,
            "likes_count": likes_count,
            "comments_count": comments_count,
            "edit_count": post.edit_count,
        }
        return Response(data)
# =====================================================================================



class AuthorStatsAPIView(APIView):
    """
    GET -> aggregated stats for one author, like HTML dashboard:
    total_posts, total_views, self/external views, likes, comments, avg_views.
    Only staff (admin/editor) can access.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        User = get_user_model()
        author = get_object_or_404(User, pk=user_id)

        posts = Post.objects.filter(author=author)

        total_posts = posts.count()
        aggregate = posts.aggregate(total_views=Sum("view_count"))
        total_views = aggregate["total_views"] or 0

        self_views = ViewEvent.objects.filter(
            post__author=author,
            user=author,
        ).count()
        external_views = total_views - self_views if total_views else 0

        total_likes = Like.objects.filter(post__author=author).count()
        total_comments = Comment.objects.filter(
            post__author=author,
            status=Comment.STATUS_APPROVED,
        ).count()

        avg_views = total_views / total_posts if total_posts > 0 else 0

        data = {
            "author_id": author.id,
            "author_username": author.username,
            "total_posts": total_posts,
            "total_views": total_views,
            "self_views": self_views,
            "external_views": external_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_views_per_post": avg_views,
        }
        return Response(data)


# ==================================================================================================

class PostViewsPerDayAPIView(generics.ListAPIView):
    """
    GET /api/posts/<slug>/views-per-day/
    -> daily view counts for a post, with optional start/end filtering.
    Staff/admin only.
    """
    permission_classes = [IsAdminUser]
    serializer_class = DailyViewsSerializer
    pagination_class = DailyViewsPagination

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        post = get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)

        # Base queryset
        qs = ViewEvent.objects.filter(post=post)

        # Optional date filters: ?start=YYYY-MM-DD&end=YYYY-MM-DD
        start_param = self.request.query_params.get("start")
        end_param = self.request.query_params.get("end")

        if start_param:
            start_date = parse_date(start_param)
            if start_date:
                qs = qs.filter(created_at__date__gte=start_date)

        if end_param:
            end_date = parse_date(end_param)
            if end_date:
                qs = qs.filter(created_at__date__lte=end_date)

        # Aggregate per date
        daily = (
            qs.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(views=Count("id"))
            .order_by("date")
        )

        # This returns a queryset of dicts: {"date": <date>, "views": <int>}
        return daily


# ==================================================================================================
class PostSearchAPIView(generics.ListAPIView):
    """
    GET /api/search/?q=... -> list of published posts matching query
    (title, author, category, tags).
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PostSerializer

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()

        base_qs = (
            Post.objects
            .filter(status=Post.STATUS_PUBLISHED)
            .select_related("author", "category")
            .prefetch_related("tags")
        )

        if not query:
            # No query provided => return empty list
            return base_qs.none()

        qs = (
            base_qs
            .filter(
                Q(title__icontains=query)
                | Q(author__username__icontains=query)
                | Q(category__name__icontains=query)
                | Q(tags__name__icontains=query)
            )
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count(
                    "comments",
                    filter=Q(comments__status=Comment.STATUS_APPROVED),
                    distinct=True,
                ),
            )
            .order_by("-published_at")
            .distinct()
        )
        return qs
