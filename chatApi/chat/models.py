from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime


class Conversation(models.Model):
    TYPE_DIRECT = "direct"
    TYPE_ROOM = "room"

    TYPE_CHOICES = [
        (TYPE_DIRECT, "direct"),
        (TYPE_ROOM, "room")
    ]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_DIRECT)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ConversationParticipant",
        related_name="conversations"
    )

    class Meta:
        indexes = [
            models.Index(fields=["type", "last_message_at"])
        ]

    def __str__(self):
        return f"{self.get_type_display()} #{self.pk} {self.title}"

    def unread_count_for(self, user):

        try:
            cp = self.participants_through.get(user=user)
            if cp.last_read_at:
                last_read = cp.last_read_at
            else:
                last_read = timezone.make_aware(datetime.datetime.min)
        except ConversationParticipant.DoesNotExist:
            return 0

        return self.messages.exclude(sender=user).filter(created_at__gt=last_read).count()


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="participants_through"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_participations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("conversation", "user"),)
        indexes = [
            models.Index(fields=["user", "conversation"])
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"])
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Conversation.objects.filter(pk=self.conversation_id).update(last_message_at=self.created_at)

    def __str__(self):
        return f"Msg#{self.pk} by User#{self.sender_id} in Conv#{self.conversation_id}"
