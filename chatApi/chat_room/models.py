from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Room(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_group:
            return self.name or f"Group Room {self.id}"
        return f"Private Room {self.id}"


class RoomParticipant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="room_participations")

    class Meta:
        unique_together = ("room", "user")

    def __str__(self):
        return f"{self.user} in {self.room}"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_room_sent_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )

    def __str__(self):
        return f"{self.sender} in {self.room}: {self.content[:20]}"
