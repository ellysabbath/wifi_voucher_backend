from django.urls import path

from . import views

app_name = "gallery"

urlpatterns = [
    path("", views.GalleryListView.as_view(), name="list-create"),
    path("<uuid:pk>/", views.GalleryDetailView.as_view(), name="detail"),
]