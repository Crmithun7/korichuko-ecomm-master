from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Store (customer site) at root
    path("", include(("store.urls", "store"), namespace="store")),

    # Adminpanel (staff portal)
    path("dashboard/", include(("adminpanel.urls", "adminpanel"), namespace="adminpanel")),
]

# Only serve /media/ from Django during local dev and when not using Cloudinary
if settings.DEBUG and not getattr(settings, "USE_CLOUD_MEDIA", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
