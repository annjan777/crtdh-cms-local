"""Test-only URLconf: the real one mounts /admin/ only when DEBUG and DJANGO_ADMIN_ENABLED."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("config.urls")),
]
