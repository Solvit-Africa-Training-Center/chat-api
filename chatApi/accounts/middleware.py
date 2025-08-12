from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

class UpdateLastSeenMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            User = get_user_model()
            User.objects.filter(pk=user.pk).update(last_seen=timezone.now())
        return response