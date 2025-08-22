from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from chat_room.models import Thread, ThreadParticipant, Message

User = get_user_model()


class ChatRoomTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass123")
        self.user2 = User.objects.create_user(username="user2", password="pass123")
        self.user3 = User.objects.create_user(username="user3", password="pass123")

        self.client.force_authenticate(user=self.user1)

    def create_thread_with_participants(self, is_group=False, participants=None, name=""):
        thread = Thread.objects.create(is_group=is_group, name=name, created_by=self.user1)
        # ensure creator is participant
        ThreadParticipant.objects.get_or_create(thread=thread, user=self.user1)
        if participants:
            for user in participants:
                ThreadParticipant.objects.get_or_create(thread=thread, user=user)
        return thread

    def test_create_private_thread(self):
        url = reverse("thread-list")
        data = {"is_group": False, "name": "", "participant_ids": [self.user2.id]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        thread_id = response.data["id"]
        thread = Thread.objects.get(id=thread_id)
        self.assertFalse(thread.is_group)
        participant_ids = [p.user.id for p in thread.participants.all()]
        self.assertIn(self.user1.id, participant_ids)
        self.assertIn(self.user2.id, participant_ids)

    def test_create_group_thread(self):
        url = reverse("thread-list")
        data = {"is_group": True, "name": "My Group", "participant_ids": [self.user2.id, self.user3.id]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        thread = Thread.objects.get(id=response.data["id"])
        self.assertTrue(thread.is_group)
        participant_ids = [p.user.id for p in thread.participants.all()]
        self.assertEqual(len(participant_ids), 3)
        self.assertIn(self.user1.id, participant_ids)
        self.assertIn(self.user2.id, participant_ids)
        self.assertIn(self.user3.id, participant_ids)

    def test_send_message(self):
        thread = self.create_thread_with_participants(participants=[self.user2])
        url = reverse("thread-messages", kwargs={"thread_id": thread.id})
        data = {"content": "Hello!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get(pk=response.data["id"])
        self.assertEqual(message.content, "Hello!")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.thread, thread)

    def test_message_threading(self):
        thread = self.create_thread_with_participants(participants=[self.user2])
        parent_msg = Message.objects.create(thread=thread, sender=self.user1, content="Parent")
        url = reverse("thread-messages", kwargs={"thread_id": thread.id})
        data = {"content": "Reply", "reply_to": parent_msg.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reply_msg = Message.objects.get(pk=response.data["id"])
        self.assertEqual(reply_msg.reply_to, parent_msg)

    def test_unread_count_and_last_seen(self):
        thread = self.create_thread_with_participants(participants=[self.user2])
        Message.objects.create(thread=thread, sender=self.user2, content="Hi user1")
        participant = ThreadParticipant.objects.get(thread=thread, user=self.user1)
        self.assertIsNone(participant.last_read_at)
        participant.last_read_at = timezone.now()
        participant.save()
        self.assertIsNotNone(participant.last_read_at)

    def test_permission_for_non_participant(self):
        thread = self.create_thread_with_participants(participants=[self.user2, self.user3])
        url = reverse("thread-messages", kwargs={"thread_id": thread.id})
        response = self.client.get(url)
        # import pdb; pdb.set_trace()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
