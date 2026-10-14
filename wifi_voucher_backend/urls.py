from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/admin/accounts/", include("accounts.admin_urls")),
    path("api/books/", include("books.urls")),
    path("api/ministries/", include("ministries.urls")),
    path("api/events/", include("events.urls")),
    path("api/news/", include("news.urls")),
    path("api/gallery/", include("gallery.urls")),
    path("api/leaders/", include("leaders.urls")),
    path("api/sms/", include("sms.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)