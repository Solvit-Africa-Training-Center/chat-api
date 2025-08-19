from unittest.mock import patch
from django.test import override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import User
from django.urls import reverse
from django.core import mail
from accounts.tasks import send_welcome_email


User = get_user_model()

@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class RegisterViewTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("register-list")
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"
        }
    
    @patch("accounts.views.send_welcome_email.delay")
    def test_user_registration_and_send_email(self, mock_send_email):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="testuser")
        self.assertIsNotNone(user)

        send_welcome_email(user.id)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome", mail.outbox[0].subject)


    def test_registration_rejects_duplicate_username(self):
        """
        Username must be unique (Django's AbstractUser enforces this).
        """
        # Create the first user
        User.objects.create_user(username="chris", email="c@e.com", password="pass123")
        payload = {
            "username": "chris",
            "email": "chris@example.com",
            "password": "123pass",
        }
        resp = self.client.post("/register/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("username", resp.data)