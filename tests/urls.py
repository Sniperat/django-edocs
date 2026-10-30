from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/edocs/", include("edocs.api.urls", namespace="edocs")),
]
