from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Thread, ThreadParticipant, Message

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class RoomMessageSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer(read_only=True)
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        required=False,
        allow_null=True
    )
    thread = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "thread", "sender", "content", "reply_to", "created_at", "updated_at"]
        read_only_fields = ["id", "sender", "thread", "created_at", "updated_at"]


class ThreadParticipantSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)

    class Meta:
        model = ThreadParticipant
        fields = ["user", "is_admin", "joined_at", "last_read_at", "last_seen_at"]
        read_only_fields = fields


class ThreadCreateSerializer(serializers.Serializer):
    is_group = serializers.BooleanField(default=False)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )


class ThreadSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = [
            "id", "is_group", "name", "created_by", "created_at", "updated_at",
            "participants", "last_message", "unread_count",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at",
                            "participants", "last_message", "unread_count"]

    def get_participants(self, obj: Thread):
        q = ThreadParticipant.objects.filter(thread=obj).select_related("user")
        return ThreadParticipantSerializer(q, many=True).data

    def get_last_message(self, obj: Thread):
        m = obj.messages.order_by("-created_at").first()
        return RoomMessageSerializer(m).data if m else None

    def get_unread_count(self, obj: Thread):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        try:
            tp = ThreadParticipant.objects.get(thread=obj, user=request.user)
        except ThreadParticipant.DoesNotExist:
            return 0
        last_read = tp.last_read_at or None
        qs = obj.messages.exclude(sender=request.user)
        if last_read:
            qs = qs.filter(created_at__gt=last_read)
        return qs.count()
