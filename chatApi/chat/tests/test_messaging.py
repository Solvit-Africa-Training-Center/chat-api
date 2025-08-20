from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from chat.models import Conversation

User = get_user_model()


class MessagingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.kenny = User.objects.create_user(username="kenny", password="1234")
        self.kevin = User.objects.create_user(username="kevin", password="1234")

        def login_as(user):
            resp = self.client.post("/login/", {"username": user.username, "password": "1234"}, format="json")
            assert resp.status_code == 200, resp.data
            access = resp.data["access"]
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        
        self.login_as = login_as

    def test_create_or_get_direct_conversation(self):
        self.login_as(self.kenny)

        resp1 = self.client.post("/api/conversations/direct/", {"other_user_id": self.kevin.id}, format="json")
        self.assertIn(resp1.status_code, [201, 200])
        conv_id = resp1.data["id"]

        resp2 = self.client.post("/api/conversations/direct/", {"other_user_id": self.kevin.id}, format="json")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["id"], conv_id)

        convo = Conversation.objects.get(pk=conv_id)
        users = set(convo.participants.values_list("username", flat=True))
        self.assertEqual(users, {"kenny", "kevin"})

    def test_send_message_and_unread_counts(self):
        self.login_as(self.kenny)
        conv = self.client.post("/api/conversations/direct/", {"other_user_id": self.kevin.id}, format="json").data
        conv_id = conv["id"]

        msg = self.client.post("/api/messages/", {"conversation": conv_id, "content": "hello bro"}, format="json")
        self.assertEqual(msg.status_code, 201)

        my_unread = self.client.get(f"/api/conversations/{conv_id}/unread_count/")
        self.assertEqual(my_unread.status_code, 200)
        self.assertEqual(my_unread.data["unread_count"], 0)

        self.login_as(self.kevin)
        kevin_unread = self.client.get(f"/api/conversations/{conv_id}/unread_count/")
        self.assertEqual(kevin_unread.status_code, 200)
        self.assertEqual(kevin_unread.data["unread_count"], 1)

    def test_mark_read_clears_unread(self):
        self.login_as(self.kenny)
        conv = self.client.post("/api/conversations/direct/", {"other_user_id": self.kevin.id}, format="json").data
        conv_id = conv["id"]

        self.client.post("/api/messages/", {"conversation": conv_id, "content": "hi"}, format="json")
        self.client.post("/api/messages/", {"conversation": conv_id, "content": "how are you"}, format="json")

        self.login_as(self.kevin)
        before = self.client.get(f"/api/conversations/{conv_id}/unread_count/")
        self.assertEqual(before.data["unread_count"], 2)

        mark = self.client.post(f"/api/conversations/{conv_id}/mark_read/")
        self.assertEqual(mark.status_code, 200)

        after = self.client.get(f"/api/conversations/{conv_id}/unread_count/")
        self.assertEqual(after.data["unread_count"], 0)
