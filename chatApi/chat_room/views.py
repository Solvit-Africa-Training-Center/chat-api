from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Thread, ThreadParticipant, Message
from .serializers import ThreadSerializer, ThreadCreateSerializer, RoomMessageSerializer

User = get_user_model()


class ThreadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Thread.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return ThreadCreateSerializer
        return ThreadSerializer

    def get_queryset(self):
        user = self.request.user
        return Thread.objects.filter(participants__user=user).distinct().order_by("-updated_at")

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        is_group = data.get("is_group", False)
        name = data.get("name", "")
        participant_ids = data["participant_ids"]

        if not is_group:
            # Direct message: reuse existing 1:1 thread if exists
            other_id = participant_ids[0]
            candidates = (
                Thread.objects.filter(is_group=False)
                .filter(participants__user=user)
                .filter(participants__user_id=other_id)
                .annotate(pcount=Count("participants"))
                .filter(pcount=2)
            )
            thread = candidates.first()
            if not thread:
                thread = Thread.objects.create(is_group=False, created_by=user)
                ThreadParticipant.objects.bulk_create([
                    ThreadParticipant(thread=thread, user=user),
                    ThreadParticipant(thread=thread, user_id=other_id),
                ])
        else:
            # Group thread
            thread = Thread.objects.create(is_group=True, name=name, created_by=user)
            memberships = [ThreadParticipant(thread=thread, user=user, is_admin=True)]
            for uid in participant_ids:
                if uid == user.id:
                    continue
                memberships.append(ThreadParticipant(thread=thread, user_id=uid))
            ThreadParticipant.objects.bulk_create(memberships)

        self.thread = thread

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        out = ThreadSerializer(self.thread, context={"request": request})
        headers = {"Location": f"/api/threads/{self.thread.pk}/"}
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        thread = self.get_object()
        tp = get_object_or_404(ThreadParticipant, thread=thread, user=request.user)
        tp.last_read_at = timezone.now()
        tp.save(update_fields=["last_read_at"])
        return Response({"status": "ok", "last_read_at": tp.last_read_at})


class MessageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomMessageSerializer

    def get_queryset(self):
        thread_id = self.kwargs["thread_id"]
        try:
            thread = Thread.objects.get(pk=thread_id)
        except Thread.DoesNotExist:
            raise PermissionDenied("Thread not found")

        if not ThreadParticipant.objects.filter(thread=thread, user=self.request.user).exists():
            raise PermissionDenied("You are not a participant")

        return thread.messages.select_related("sender", "reply_to")

    def perform_create(self, serializer):
        thread_id = self.kwargs["thread_id"]
        try:
            thread = Thread.objects.get(pk=thread_id)
        except Thread.DoesNotExist:
            raise PermissionDenied("Thread not found")

        if not ThreadParticipant.objects.filter(thread=thread, user=self.request.user).exists():
            raise PermissionDenied("You are not a participant")

        serializer.save(thread=thread, sender=self.request.user)
