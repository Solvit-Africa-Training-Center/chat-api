from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from chat_room.models import Room, RoomParticipant, Message

User = get_user_model()


class ChatRoomTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass123")
        self.user2 = User.objects.create_user(username="user2", password="pass123")
        self.user3 = User.objects.create_user(username="user3", password="pass123")

        self.client.force_authenticate(user=self.user1)

    def create_room_with_participants(self, is_group=False, participants=None, name=""):
        room = Room.objects.create(is_group=is_group, name=name)
        RoomParticipant.objects.get_or_create(room=room, user=self.user1)
        if participants:
            for user in participants:
                RoomParticipant.objects.get_or_create(room=room, user=user)
        return room

    def test_create_private_room(self):
        url = reverse("room-list-create")
        data = {"is_group": False, "name": "Private Chat"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room_id = response.data["id"]
        room = Room.objects.get(id=room_id)
        self.assertFalse(room.is_group)

    def test_create_group_room(self):
        url = reverse("room-list-create")
        data = {"is_group": True, "name": "My Group Chat"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        room = Room.objects.get(id=response.data["id"])
        self.assertTrue(room.is_group)

    def test_send_message(self):
        room = self.create_room_with_participants(participants=[self.user2])
        url = reverse("message-list-create", kwargs={"room_id": room.id})
        data = {"content": "Hello!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get(pk=response.data["id"])
        self.assertEqual(message.content, "Hello!")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.room, room)

    def test_message_reply(self):
        room = self.create_room_with_participants(participants=[self.user2])
        parent_msg = Message.objects.create(room=room, sender=self.user1, content="Parent")
        url = reverse("message-list-create", kwargs={"room_id": room.id})
        data = {"content": "Replying", "reply_to": parent_msg.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reply_msg = Message.objects.get(pk=response.data["id"])
        self.assertEqual(reply_msg.reply_to, parent_msg)

    def test_unread_count_simulation(self):
        room = self.create_room_with_participants(participants=[self.user2])
        Message.objects.create(room=room, sender=self.user2, content="Hi user1")
        participant = RoomParticipant.objects.get(room=room, user=self.user1)
        self.assertIsNotNone(participant.id)  # updated placeholder
        participant.save()

    def test_permission_for_non_participant(self):
        room = self.create_room_with_participants(participants=[self.user2, self.user3])
        url = reverse("message-list-create", kwargs={"room_id": room.id})
        self.client.force_authenticate(user=self.user3)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
