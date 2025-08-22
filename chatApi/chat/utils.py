from django.utils import timezone
from .models import Conversation, Message
from django.contrib.auth import get_user_model


User = get_user_model()


def get_unread_count(conversation: Conversation, user: User) -> int:
    """
    Return the number of unread messages in a conversation for a specific user.
    """
    return conversation.messages.exclude(sender=user).filter(is_read=False).count()


def mark_conversation_as_read(conversation: Conversation, user: User):
    """
    Mark all messages in a conversation as read for the current user.
    """
    conversation.messages.exclude(sender=user).filter(is_read=False).update(is_read=True)


def get_message_thread(message: Message):
    """
    Return all replies to a message, recursively.
    """
    replies = message.replies.all().order_by("created_at")
    thread = []
    for reply in replies:
        thread.append({
            "message": reply,
            "replies": get_message_thread(reply)
        })
    return thread


def get_user_last_seen_in_conversation(conversation: Conversation, user: User):
    """
    Return the last time the user was active in the conversation.
    For simplicity, you can use the last message read time or membership model.
    """
    # If you have a Membership or through model with last_seen
    membership = conversation.participants.through.objects.filter(
        conversation=conversation, user=user
    ).first()
    if membership and hasattr(membership, "last_seen"):
        return membership.last_seen
    return None


def update_user_last_seen(conversation: Conversation, user: User):
    """
    Update the user's last_seen timestamp for this conversation.
    """
    membership = conversation.participants.through.objects.filter(
        conversation=conversation, user=user
    ).first()
    if membership and hasattr(membership, "last_seen"):
        membership.last_seen = timezone.now()
        membership.save()
