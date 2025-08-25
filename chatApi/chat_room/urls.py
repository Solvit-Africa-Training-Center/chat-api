from django.urls import path
from . import views

urlpatterns = [
    path("rooms/", views.RoomListCreateView.as_view(), name="room-list-create"),
    path("rooms/<int:pk>/", views.RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:room_id>/messages/", views.MessageListCreateView.as_view(), name="message-list-create"),
]
