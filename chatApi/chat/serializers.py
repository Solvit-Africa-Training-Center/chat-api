from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserLiteSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "type", "title", "participants", "last_message_at", "unread_count"]

    def get_unread_count(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return 0
        return obj.unread_count_for(user)


class ConversationCreateSerializer(serializers.Serializer):
    other_user_id = serializers.IntegerField()

    def validate_other_user_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("User does not exist")
        return value


class MessageSerializer(serializers.ModelSerializer):
    sender = UserLiteSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "conversation", "sender", "content", "created_at")
        read_only_fields = ("id", "sender", "created_at")
