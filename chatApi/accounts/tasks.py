from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from chatApi.settings import DEFAULT_FROM_EMAIL

User = get_user_model()

@shared_task
def send_welcome_email(user_id):
    try:
        user = User.objects.get(pk=user_id)
        if not user.email:
            return "No email"
        send_mail(
            subject="Welcome to ChatApi",
            message=f"Hi {user.username}, welcome to ChatApi!!!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        return "sent"
    except User.DoesNotExist:
        return "User not found"