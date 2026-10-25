from django.urls import path
from rest_framework.routers import DefaultRouter
# from .api.views import PostViewSet, PostCommentListCreateAPIView
from .api.views import (
    PostViewSet,
    PostCommentListCreateAPIView,
    PostLikeToggleAPIView,
    PostStatsAPIView,
    AuthorStatsAPIView,
    PostSearchAPIView,
    PostViewsPerDayAPIView,
    CommentDetailAPIView
)

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")


urlpatterns = [
    path( "search/", PostSearchAPIView.as_view(), name="post-search"),
    path( "posts/<slug:slug>/comments/", PostCommentListCreateAPIView.as_view(), name="post-comments"),
    path( "posts/<slug:slug>/like/", PostLikeToggleAPIView.as_view(), name="post-like-toggle"),
    path( "posts/<slug:slug>/stats/", PostStatsAPIView.as_view(), name="post-stats"),
    path( "posts/<slug:slug>/views-per-day/", PostViewsPerDayAPIView.as_view(), name="post-views-per-day"),

    path( "authors/<int:user_id>/stats/", AuthorStatsAPIView.as_view(), name="author-stats"),
    path("comments/<int:pk>/", CommentDetailAPIView.as_view(), name="comment-detail"),
]

urlpatterns += router.urls
