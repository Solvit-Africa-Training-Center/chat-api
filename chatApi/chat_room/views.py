from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer


class RoomListCreateView(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]


class RoomDetailView(generics.RetrieveAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]


class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs.get("room_id")
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise NotFound(detail="Room not found.")

        return Message.objects.filter(room=room, room__participants__user=self.request.user)

    def create(self, request, *args, **kwargs):
        room_id = self.kwargs.get("room_id")
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise NotFound(detail="Room not found.")

        serializer = self.get_serializer(
            data=request.data, context={"room": room, "user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
