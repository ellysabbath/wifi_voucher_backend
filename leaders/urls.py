from django.urls import path

from . import views

app_name = "leaders"

urlpatterns = [
    path("", views.LeaderListView.as_view(), name="list-create"),
    path("<uuid:pk>/", views.LeaderDetailView.as_view(), name="detail"),
]