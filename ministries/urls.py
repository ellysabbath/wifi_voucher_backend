from django.urls import path

from . import views

app_name = "ministries"

urlpatterns = [
    path("", views.MinistryListView.as_view(), name="list-create"),
    path("<uuid:pk>/", views.MinistryDetailView.as_view(), name="detail"),
]