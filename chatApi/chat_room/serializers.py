from rest_framework import serializers, generics, permissions
from .models import Room, RoomParticipant, Message


class RoomParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomParticipant
        fields = ["id", "user", "room"]


class RoomSerializer(serializers.ModelSerializer):
    participants = RoomParticipantSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Room
        fields = ["id", "name", "is_group", "created_at", "participants", "participant_ids"]

    def create(self, validated_data):
        participant_ids = validated_data.pop("participant_ids", [])
        room = Room.objects.create(**validated_data)

        for user_id in participant_ids:
            RoomParticipant.objects.create(room=room, user_id=user_id)

        return room

class RoomListCreateView(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        room = serializer.save()
        RoomParticipant.objects.get_or_create(room=room, user=self.request.user)



class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "room", "sender", "content", "created_at", "reply_to"]
        read_only_fields = ["sender", "created_at", "room"]
        ref_name = "ChatRoomMessageSerializer"  # unique name


    def create(self, validated_data):
        room = self.context.get("room")
        user = self.context.get("user")
        return Message.objects.create(room=room, sender=user, **validated_data)
