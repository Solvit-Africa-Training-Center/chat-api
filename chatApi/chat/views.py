from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import Conversation, ConversationParticipant, Message
from .serializers import (
    ConversationSerializer, MessageSerializer,
    ConversationCreateSerializer,
    MessageCreateSerializer, MessageUpdateSerializer
)
from .permissions import IsConversationParticipant

User = get_user_model()


class ConversationViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or self.request.user.is_anonymous:
            return Conversation.objects.none()

        return (
            Conversation.objects
            .filter(participants=self.request.user)
            .prefetch_related("participants")
            .order_by("-last_message_at", "-id")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def direct(self, request):
        create_ser = ConversationCreateSerializer(data=request.data)
        create_ser.is_valid(raise_exception=True)
        other_id = create_ser.validated_data["other_user_id"]

        if other_id == request.user.id:
            return Response(
                {"detail": "Cannot start direct conversation with yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )

        other_user = get_object_or_404(User, pk=other_id)
        convo, created = Conversation.get_or_create_direct(request.user, other_user)
        data = ConversationSerializer(convo, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if created else 200)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsConversationParticipant])
    def mark_read(self, request, pk=None):
        convo = self.get_object()
        now = timezone.now()
        ConversationParticipant.objects.filter(conversation=convo, user=request.user).update(last_read_at=now)
        return Response({"status": "ok", "last_read_at": now})

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsConversationParticipant])
    def unread_count(self, request, pk=None):
        convo = self.get_object()
        count = convo.unread_count_for(request.user)
        return Response({"unread_count": count})


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["create"]:
            return MessageCreateSerializer
        if self.action in ["update", "partial_update"]:
            return MessageUpdateSerializer
        return MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(conversation__participants=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        convo = serializer.validated_data.get("conversation")
        recipient_id = serializer.validated_data.get("recipient_id")

        if not convo and recipient_id:
            recipient = get_object_or_404(User, pk=recipient_id)
            convo, _ = Conversation.get_or_create_direct(request.user, recipient)

        if not convo:
            return Response(
                {"detail": "You must provide either conversation_id or recipient_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg = Message.objects.create(
            conversation=convo,
            sender=request.user,
            content=serializer.validated_data.get("content", ""),
            parent=serializer.validated_data.get("parent")
        )

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)
