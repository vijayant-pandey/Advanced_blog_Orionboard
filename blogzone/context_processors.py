# from .models import Post, Tag

# def base_globals(request):
#     trending = Post.objects.filter(status=Post.STATUS_PUBLISHED).order_by('-view_count')[:5]
#     tags = Tag.objects.all()[:12]
#     popular = Post.objects.filter(status=Post.STATUS_PUBLISHED).order_by('-view_count')[:4]
#     return {
#         "trending_list": [{"title": p.title, "url": p.get_absolute_url()} for p in trending],
#         "popular_tags": tags,
#         "popular_posts": popular,
#     }


from django.urls import reverse
from .models import Post, Tag

def base_globals(request):
    trending_qs = Post.objects.filter(status=Post.STATUS_PUBLISHED).order_by('-view_count')[:5]
    trending = []
    for p in trending_qs:
        # build url safely: prefer reverse, fallback to slug path
        try:
            url = reverse('blogzone:post_detail', kwargs={'slug': p.slug})
        except Exception:
            url = f"/blog/{p.slug}/"
        trending.append({"title": p.title, "url": url})

    tags = Tag.objects.all()[:12]
    popular = Post.objects.filter(status=Post.STATUS_PUBLISHED).order_by('-view_count')[:4]
    return {
        "trending_list": trending,
        "popular_tags": tags,
        "popular_posts": popular,
    }
