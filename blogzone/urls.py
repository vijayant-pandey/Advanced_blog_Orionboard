from django.urls import path
from . import views

app_name = "blogzone"

urlpatterns = [
    
    path("about/", views.about, name="about"),
    path("gallery/", views.gallery, name="gallery"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("", views.post_list, name="post_list"),
    path("search/", views.search, name="search"),
    path("my/", views.my_posts, name="my_posts"),  # ✅ My Posts
    
    path("my/create/", views.create_post, name="create_post"),
    path("my/<slug:slug>/edit/", views.edit_post, name="edit_post"),  # 👈 new
    path("dashboard/authors/", views.author_stats, name="author_stats"),
    path("dashboard/authors/<int:user_id>/posts/", views.author_detail_stats, name="author_detail_stats"),
    path("dashboard/post/<slug:slug>/views/", views.post_views_timeseries, name="post_views_timeseries"),
    path("<slug:slug>/like/", views.toggle_like, name="toggle_like"),  # 👈 new
    path("<slug:slug>/comment/ajax/", views.ajax_comment, name="ajax_comment"),

    path("<slug:slug>/", views.post_detail, name="post_detail"),
    
]
