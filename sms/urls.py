from django.urls import path
from . import views

app_name = "sms"

urlpatterns = [
    path("groups/", views.SMSGroupListView.as_view(), name="group-list"),
    path("groups/<uuid:pk>/", views.SMSGroupDetailView.as_view(), name="group-detail"),
    path("messages/", views.SMSMessageListView.as_view(), name="message-list"),
    path("messages/<uuid:pk>/", views.SMSMessageDetailView.as_view(), name="message-detail"),
    path("send/", views.SendSMSView.as_view(), name="send"),
]