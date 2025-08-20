from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import Conversation, ConversationParticipant, Message
from .serializers import ConversationSerializer, MessageSerializer, ConversationCreateSerializer
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

        convo = (
            Conversation.objects
            .filter(type=Conversation.TYPE_DIRECT)
            .filter(participants=request.user)
            .filter(participants=other_user)
            .distinct()
            .first()
        )

        created = False
        if not convo:
            convo = Conversation.objects.create(type=Conversation.TYPE_DIRECT)
            ConversationParticipant.objects.create(conversation=convo, user=request.user)
            ConversationParticipant.objects.create(conversation=convo, user=other_user)
            created = True

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
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(conversation__participants=self.request.user)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        convo = ser.validated_data.get("conversation")
        recipient_id = request.data.get("recipient_id")

        # If no conversation is passed, auto-create/find direct convo
        if not convo and recipient_id:
            recipient = get_object_or_404(User, pk=recipient_id)
            convo, _ = Conversation.objects.get_or_create_direct(request.user, recipient)

        if not convo:
            return Response(
                {"detail": "You must provide either conversation_id or recipient_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        msg = Message.objects.create(
            conversation=convo,
            sender=request.user,
            content=ser.validated_data.get("content", ""),
            parent=ser.validated_data.get("parent")
        )

        out = self.get_serializer(msg).data
        return Response(out, status=status.HTTP_201_CREATED)

