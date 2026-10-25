from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Like, Comment, ViewEvent, Category, Tag, PostSection, FaqItem, ContactMessage, Video
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .forms import PostForm, CommentForm, ContactForm
from django.utils.text import slugify
from django.db.models import Count, Q, Sum
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden, Http404, JsonResponse, HttpResponseBadRequest
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
# from .utils import get_client_ip
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string


# ... your existing views ...




# =========================================================================
def get_client_ip(request):
    """
    Best-effort method to get client IP.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # In case of multiple IPs, take the first
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip




# =========================================================================
def can_manage_posts(user):
    """ Returns True if the user is in Admin, Editor, or Author group, or is a superuser. """
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(name__in=["Admin", "Editor", "Author"]).exists()
# =========================================================================

def can_view_dashboard(user):
    """
    Only Admins, Editors, or superusers can view analytics dashboard.
    """
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(name__in=["Admin", "Editor"]).exists()


# =========================================================================

# def post_list(request):
#     posts = (
#         Post.objects
#         .filter(status=Post.STATUS_PUBLISHED)
#         .annotate(
#             likes_count=Count("likes", distinct=True),
#             comments_count=Count(
#                 "comments",
#                 filter=Q(comments__status=Comment.STATUS_APPROVED),
#                 distinct=True
#             ),
#         )
#         .order_by("-published_at")
#     )
#     return render(request, "blogzone/post_list.html", {"posts": posts})

# WIth Popular and Recent Features
def post_list(request):
    # Recent posts (for main grid/list + "Recent" tab)
    posts = (
        Post.objects
        .filter(status=Post.STATUS_PUBLISHED)
        .annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count(
                "comments",
                filter=Q(comments__status=Comment.STATUS_APPROVED),
                distinct=True
            ),
        )
        .order_by("-published_at")
    )

    # Popular / Featured posts – manual control via is_featured
    popular_posts = (
        Post.objects
        .filter(status=Post.STATUS_PUBLISHED, is_featured=True)
        .annotate(
            likes_count=Count("likes", distinct=True),
            comments_count=Count(
                "comments",
                filter=Q(comments__status=Comment.STATUS_APPROVED),
                distinct=True
            ),
        )
        .order_by("-published_at")[:5]  # show top 5 featured posts
    )

    # 👇 NEW: fetch one active sidebar video
    sidebar_video = Video.objects.filter(is_active=True).order_by("display_order", "-created_at").first()

    context = {
        "posts": posts,
        "popular_posts": popular_posts,
        "sidebar_video": sidebar_video,
        # if you already pass popular_tags elsewhere, keep that too
    }
    return render(request, "blogzone/post_list.html", context)


# ==================================================================================
def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

# =========================================================================
def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)


    # Track views only for GET requests
    if request.method == "GET":
        post.view_count = (post.view_count or 0) + 1
        post.save(update_fields=["view_count"])

        ViewEvent.objects.create(
            post=post,
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            country="",  # to be filled by GeoIP later
            city="",     # to be filled by GeoIP later
        )

    # Likes info
    likes_count = post.likes.count()
    has_liked = False
    if request.user.is_authenticated:
        has_liked = Like.objects.filter(post=post, user=request.user).exists()

    # Handle new comment (root or reply)
    if request.method == "POST":
        if not request.user.is_authenticated:
            # return redirect("login")
            return redirect(f"{reverse('login')}?next={request.path}")


        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user

            # Handle parent (for replies)
            # parent_id = request.POST.get("parent_id")
            # if parent_id:
            #     try:
            #         parent = Comment.objects.get(id=parent_id, post=post)
            #         comment.parent = parent
            #     except Comment.DoesNotExist:
            #         comment.parent = None

            # # New comments start as pending
            # comment.status = Comment.STATUS_PENDING
            # comment.save()
            # return redirect("blogzone:post_detail", slug=slug)
            parent_id = request.POST.get("parent_id")
            if parent_id:
                parent = Comment.objects.filter(
                    id=parent_id,
                    post=post,
                ).first()
                if parent:
                    comment.parent = parent

            # default status = pending / or approved per your logic
            # comment.status = Comment.STATUS_PENDING
            comment.save()
            messages.success(request, "Your comment has been submitted for review.")
            return redirect("blogzone:post_detail", slug=post.slug)
    else:
        form = CommentForm()
    
    # Only approved comments are displayed
    approved_comments = Comment.objects.filter(
        post=post,
        status=Comment.STATUS_APPROVED,
    ).select_related("user")

    # Only approved comments are displayed
    all_comments = post.comments.filter(status=Comment.STATUS_APPROVED).select_related("user")

    # Root comments (parent is None)
    root_comments = approved_comments.filter(parent__isnull=True)

    comments_count = all_comments.count()

    # 👇 NEW: fetch one active sidebar video
    sidebar_video = Video.objects.filter(is_active=True).order_by("display_order", "-created_at").first()

    # For nested display, replies are accessible via comment.replies.all
    context = {
        "post": post,
        "likes_count": likes_count,
        "has_liked": has_liked,
        "form": form,
        "root_comments": root_comments,
        "comments_count": comments_count,
        "sidebar_video": sidebar_video, 
    }
    return render(request, "blogzone/post_detail.html", context)



# =========================================================================

@require_POST
@login_required
def ajax_comment(request, slug):
    """
    AJAX endpoint for creating comments / replies.
    Returns JSON with rendered HTML for the new comment.
    """
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return HttpResponseBadRequest("AJAX requests only")

    post = get_object_or_404(Post, slug=slug, status=Post.STATUS_PUBLISHED)

    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"ok": False, "errors": form.errors},
            status=400,
        )

    comment = form.save(commit=False)
    comment.post = post
    comment.user = request.user

    # parent = reply support
    parent_id = request.POST.get("parent_id")
    if parent_id:
        parent = Comment.objects.filter(id=parent_id, post=post).first()
        if parent:
            comment.parent = parent

    # keep them pending for moderation
    comment.status = Comment.STATUS_PENDING
    comment.save()

    # how many approved comments are visible
    comments_count = Comment.objects.filter(
        post=post,
        status=Comment.STATUS_APPROVED,
    ).count()

    # Render the HTML snippet for the *new comment or reply*
    # You should already have a partial template; if not, you can create it.
    html = render_to_string(
        "blogzone/_comment_item.html",   # <-- use your partial name
        {"comment": comment, "user": request.user},
        request=request,
    )

    return JsonResponse({
        "ok": True,
        "message": "Your comment has been submitted for review.",
        "is_reply": bool(comment.parent_id),
        "parent_id": comment.parent_id,
        "comments_count": comments_count,
        "html": html,
    })
# =============================================================================


@login_required
def toggle_like(request, slug):
    post = get_object_or_404(Post, slug=slug)

    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        # Like already existed -> unlike (delete it)
        like.delete()

    return redirect("blogzone:post_detail", slug=slug)

# =========================================================================
@login_required
def my_posts(request):
    posts = Post.objects.filter(author=request.user)
    return render(request, "blogzone/my_posts.html", {"posts": posts})

# =========================================================================
@login_required
@user_passes_test(can_view_dashboard)
def author_stats(request):
    if not can_view_dashboard(request.user):
        raise Http404("Page not found")
    User = get_user_model()

    authors = (
        User.objects
        .filter(posts__isnull=False)  # users that have at least one post
        .annotate(
            total_posts=Count("posts", distinct=True),
            total_views=Sum("posts__view_count"),
            total_likes=Count("posts__likes", distinct=True),
            total_comments=Count(
                "posts__comments",
                filter=Q(posts__comments__status=Comment.STATUS_APPROVED),
                distinct=True,
            ),
        )
        .order_by("-total_views", "-total_posts")
    )

    # Compute average views per post (in Python, so we don't divide by zero)
    author_data = []
    for author in authors:
        total_posts = author.total_posts or 0
        total_views = author.total_views or 0

        # Self views: where the viewer is the author of the post
        self_views = ViewEvent.objects.filter(
            post__author=author,
            user=author,
        ).count()

        external_views = total_views - self_views if total_views else 0

        avg_views = total_views / total_posts if total_posts > 0 else 0

        author_data.append({
            "author": author,
            "total_posts": total_posts,
            "total_views": total_views,
            "self_views": self_views,
            "external_views": external_views,
            "total_likes": author.total_likes or 0,
            "total_comments": author.total_comments or 0,
            "avg_views": avg_views,
        })

    context = {
        "author_data": author_data,
    }
    return render(request, "blogzone/author_stats.html", context)



# =========================================================================
@login_required
@user_passes_test(can_view_dashboard)
def author_detail_stats(request, user_id):
    User = get_user_model()
    author = get_object_or_404(User, pk=user_id)

    posts = Post.objects.filter(author=author)

    post_data = []
    for post in posts:
        total_views = post.view_count or 0
        self_views = ViewEvent.objects.filter(post=post, user=author).count()
        external_views = total_views - self_views if total_views else 0

        likes_count = Like.objects.filter(post=post).count()
        comments_count = Comment.objects.filter(
            post=post,
            status=Comment.STATUS_APPROVED,
        ).count()

        post_data.append({
            "post": post,
            "total_views": total_views,
            "self_views": self_views,
            "external_views": external_views,
            "likes_count": likes_count,
            "comments_count": comments_count,
        })

    context = {
        "author": author,
        "post_data": post_data,
    }
    return render(request, "blogzone/author_detail_stats.html", context)
# =============================================================================

@login_required
@user_passes_test(can_view_dashboard)
def post_views_timeseries(request, slug):
    post = get_object_or_404(Post, slug=slug)

    daily_views = (
        ViewEvent.objects
        .filter(post=post)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Prepare data for template (and future charts)
    dates = [entry["date"] for entry in daily_views]
    counts = [entry["count"] for entry in daily_views]

    context = {
        "post": post,
        "daily_views": daily_views,
        "dates": dates,
        "counts": counts,
    }
    return render(request, "blogzone/post_views_timeseries.html", context)

# =========================================================================
@login_required
@user_passes_test(can_manage_posts)
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user

            # Generate a slug from title if not set
            base_slug = slugify(post.title)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            post.slug = slug

            # Only admin can actually publish; here we handle draft/pending or only staff can truly publish
            if post.status == Post.STATUS_PUBLISHED and not request.user.is_staff:
                post.status = Post.STATUS_PENDING

            # Set published_at only when status is published
            if post.status == Post.STATUS_PUBLISHED and post.published_at is None:
                post.published_at = timezone.now()
                

            post.save()

            # Handle tags
            tags_input = form.cleaned_data.get("tags_input", "")
            from .models import Tag, Category
            tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]
            tag_objs = []
            for name in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=name)
                tag_objs.append(tag_obj)
                # auto-add categories from tags if not exist
                Category.objects.get_or_create(name=name)
            if tag_objs:
                post.tags.set(tag_objs)

            # Handle dynamic sections
            headings = request.POST.getlist("section_heading[]")
            contents = request.POST.getlist("section_content[]")
            images = request.FILES.getlist("section_image[]")

            from .models import PostSection
            for idx, content in enumerate(contents):
                content = content.strip()
                if not content:
                    continue  # skip empty sections
                heading = ""
                if idx < len(headings):
                    heading = headings[idx].strip()
                image = None
                if idx < len(images):
                    image = images[idx]
                PostSection.objects.create(
                    post=post,
                    order=idx,
                    heading=heading,
                    content=content,
                    image=image,
                )


            # Redirect to the post detail page
            return render(request, "blogzone/post_created_success.html", {"post": post})
    else:
        form = PostForm(user=request.user)

    return render(request, "blogzone/create_post.html", {"form": form})

# =========================================================================

@login_required
@user_passes_test(can_manage_posts)
def edit_post(request, slug):
    post = get_object_or_404(Post, slug=slug)

    # Only allow: superuser, Admin/Editor, or the post's own author
    is_editor_or_admin = request.user.is_superuser or request.user.groups.filter(
        name__in=["Admin", "Editor"]
    ).exists()

    if not (is_editor_or_admin or post.author == request.user):
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post, user=request.user)
        if form.is_valid():
            # Count as an edit only if something changed
            if form.has_changed():
                edited_post = form.save(commit=False)
                edited_post.edit_count = (post.edit_count or 0) + 1

                # If status is published and no published_at, set it -- published_at logic
                if edited_post.status == Post.STATUS_PUBLISHED and edited_post.published_at is None:
                    edited_post.published_at = timezone.now()
                
                # Same logic: non-staff cannot directly publish -- non-staff cannot publish directly
                if edited_post.status == Post.STATUS_PUBLISHED and not request.user.is_staff:
                    edited_post.status = Post.STATUS_PENDING

                edited_post.save()
            else:
                form.save()  # No changes, just save
            

            # Handle tags
            tags_input = form.cleaned_data.get("tags_input", "")
            from .models import Tag, Category, PostSection
            tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]
            tag_objs = []
            for name in tag_names:
                tag_obj, _ = Tag.objects.get_or_create(name=name)
                tag_objs.append(tag_obj)
                Category.objects.get_or_create(name=name)
            if tag_objs:
                post.tags.set(tag_objs)

            # Replace sections
            PostSection.objects.filter(post=post).delete()

            headings = request.POST.getlist("section_heading[]")
            contents = request.POST.getlist("section_content[]")
            images = request.FILES.getlist("section_image[]")

            for idx, content in enumerate(contents):
                content = content.strip()
                if not content:
                    continue
                heading = ""
                if idx < len(headings):
                    heading = headings[idx].strip()
                image = None
                if idx < len(images):
                    image = images[idx]
                PostSection.objects.create(
                    post=post,
                    order=idx,
                    heading=heading,
                    content=content,
                    image=image,
                )

            # return redirect("blogzone:post_detail", slug=post.slug)
            # Better redirect:
            if post.status == Post.STATUS_PUBLISHED:
                return redirect("blogzone:post_detail", slug=post.slug)
            else:
                return redirect("blogzone:my_posts")
    else:
        form = PostForm(instance=post, user=request.user)
    
    # also pass sections for editing (see next section)
    # sections = PostSection.objects.filter(post=post).order_by("order")

    return render(request, "blogzone/edit_post.html", {"form": form, "post": post})

# =========================================================================
def search(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        results = (
            Post.objects.filter(
                Q(status=Post.STATUS_PUBLISHED),
                Q(title__icontains=query)
                | Q(author__username__icontains=query)
                | Q(category__name__icontains=query)
                | Q(tags__name__icontains=query),
            )
            .select_related("author", "category")
            .prefetch_related("tags")
            .distinct()
        )

    context = {
        "query": query,
        "results": results,
    }
    return render(request, "blogzone/search_results.html", context)


# ================================================================================================
def about(request):
    return render(request, "blogzone/about.html")

# ================================================================================================


def gallery(request):
    """
    Show all images from:
    - Post.cover_image
    - PostSection.image
    for published posts only.
    """
    # All published posts that actually have a file in cover_image
    post_images = (
        Post.objects
        .filter(status=Post.STATUS_PUBLISHED)
        .exclude(Q(cover_image="") | Q(cover_image__isnull=True))
        .only("id", "slug", "title", "cover_image", "published_at")
        .order_by("-published_at")          # newest posts first
    )

    # All PostSection images for published posts that actually have a file
    section_images = (
        PostSection.objects
        .filter(post__status=Post.STATUS_PUBLISHED)
        .exclude(Q(image="") | Q(image__isnull=True))
        .select_related("post")
        .only("id", "post__slug", "post__title", "heading", "image", "post__published_at")
        .order_by("-post__published_at", "order")   # newest post sections first
    )

    context = {
        "post_images": post_images,
        "section_images": section_images,
    }
    return render(request, "blogzone/gallery.html", context)

# ===========================================================================================
# def faq(request):
#     """
#     Show admin-editable FAQs.
#     """
#     faqs = FaqItem.objects.filter(is_active=True).order_by("display_order", "id")
#     return render(request, "blogzone/faq.html", {"faqs": faqs})



def faq(request):
    """
    Show admin-manageable FAQs in two columns.
    """
    faqs_qs = FaqItem.objects.filter(is_active=True).order_by("display_order", "id")

    # split into two lists for left/right columns
    faqs_left = []
    faqs_right = []
    for idx, item in enumerate(faqs_qs):
        if idx % 2 == 0:
            faqs_left.append(item)
        else:
            faqs_right.append(item)

    context = {
        "faqs_left": faqs_left,
        "faqs_right": faqs_right,
    }
    return render(request, "blogzone/faq.html", context)

# ===========================================================================================


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save()

            # Optional: send email (will use console backend in dev)
            subject = contact_msg.subject or "New contact message"
            body = (
                f"Name: {contact_msg.first_name} {contact_msg.last_name}\n"
                f"Email: {contact_msg.email}\n"
                f"Phone: {contact_msg.phone}\n\n"
                f"Message:\n{contact_msg.message}"
            )
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[getattr(settings, "CONTACT_RECIPIENT_EMAIL", settings.DEFAULT_FROM_EMAIL)],
                    fail_silently=True,
                )
            except Exception:
                # In dev, we can safely ignore errors; message still saved in DB
                pass

            messages.success(request, "Thank you! Your message has been sent.")
            return redirect("blogzone:contact")
    else:
        form = ContactForm()

    return render(request, "blogzone/contact.html", {"form": form})

# ========================================================================================================
def custom_404(request, exception):
    # you can log stuff here if you want
    return render(request, "blogzone/404.html", status=404)

# ======================================================================================================
