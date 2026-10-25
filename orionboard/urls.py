from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import home, logout_view  # 👈 add logout_view here
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from blogzone import views as blog_views



urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("blog/", include("blogzone.urls")),  # 👈 add this line

    path("api/", include("blogzone.api_urls")),  # 👈 DRF API base

    # JWT endpoints
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # Custom logout that allows GET
    path("accounts/logout/", logout_view, name="logout"),
    
    # Django's built-in auth views (login, password change, etc.)
    path("accounts/", include("django.contrib.auth.urls")),  # ✅ LOGIN / LOGOUT

    
]

# custom error handlers
handler404 = "blogzone.views.custom_404"

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

