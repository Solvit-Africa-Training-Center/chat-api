from multiprocessing import context
from django.db.models import Count
from django.shortcuts import get_list_or_404
from django.utils import timezone
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, ConversationParticipant, Message
from .serializers import ConversationSerializer, MessageSerializer
from .permissions import IsConversationParticipant



class ConversationViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).select_related().prefetch_related("participants").order_by("-last_message_at", "-id")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)
    
    @action(detail=False, methods=["post"])
    def direct(self, request):
        create_ser = ConversationSerializer(data=request.data)
        create_ser.is_valid(raise_exception=True)
        other_id = create_ser.validated_data["other_user_id"]

        if other_id == request.user.id:
            return Response({"detail": "Cannot start direct conversation with yourself"}, status=status.HTTP_400_BAD_REQUEST)
        
        qs = (
            Conversation.objects
            .filter(type=Conversation.TYPE_DIRECT, participants=request.user)
            .filter(participants__id=other_id)
            .annotate(num_participants=Count("participants"))
            .filter(num_participants=2)
        )
        convo = qs.first()

        if not convo:
            convo = Conversation.objects.create(type=Conversation.TYPE_DIRECT)
            ConversationParticipant.objects.create(conversation=convo, user=request.user)
            ConversationParticipant.objects.create(conversation=convo, user_id=other_id)

        data = ConversationSerializer(convo, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if qs.first() is None else 200)
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsConversationParticipant])
    def mark_read(self, request, pk=None):
        convo = self.get_object()
        now = timezone.now()
        ConversationParticipant.objects.filter(conversation=convo, user=request.user).update(last_read_at=now)
        return Response({"status": "ok", "last_read_at":now})
    

class MessageViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin):
    permission_classes = [IsAuthenticated, IsConversationParticipant]
    serializer_class = MessageSerializer
    queryset = Message.objects.all().select_related("conversation", "sender")

    def list(self, request, *args, **kwargs):
        Conversation_id = request.query_params.get("conversation")
        convo = get_list_or_404(Conversation, pk=Conversation_id)
        self.check_object_permissions(request, convo)

        qs = (self.queryset.filter(conversation=convo).order_by("created_at"))
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)
    

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exceptio=True)

        convo  =get_list_or_404(Conversation, pk=ser.validated_data["conversation".id])
        self.check_object_permissions(request, convo)

        msg = Message.objects.create(
            conversation=convo,
            semder=request.user,
            content=ser.validated_data.get("content", ""),
            parent=ser.validated_data.get("parent")
        )

        out = self.get_serializer(msg).data
        return Response(out, status=status.HTTP_201_CREATED)