from rest_framework.permissions import BasePermission

class IsConversationParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        conversation = getattr(obj, "conversation", obj)
        return conversation.participants.filter(pk=request.user.pk).exists()