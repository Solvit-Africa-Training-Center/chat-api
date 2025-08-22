from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Thread, ThreadParticipant, Message
from .serializers import RoomMessageSerializer

User = get_user_model()

class ThreadConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        is_member = await self._is_member(user.id, self.thread_id)
        if not is_member:
            await self.close(code=4403)
            return

        self.group_name = f"thread_{self.thread_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self._update_last_seen(user.id)
        await self.accept()

    async def disconnect(self, code):
        user = self.scope.get("user")
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if user and user.is_authenticated:
            await self._update_last_seen(user.id)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        user = self.scope["user"]

        if msg_type == "message.create":
            text = (content.get("content") or "").strip()
            reply_to = content.get("reply_to")
            if not text:
                return
            message = await self._create_message(user.id, text, reply_to)
            payload = await self._serialize_message(message.id)
            await self.channel_layer.group_send(self.group_name, {
                "type": "message.created",
                "message": payload,
            })

    @database_sync_to_async
    def _is_member(self, user_id, thread_id) -> bool:
        return ThreadParticipant.objects.filter(thread_id=thread_id, user_id=user_id).exists()

    @database_sync_to_async
    def _update_last_seen(self, user_id):
        ThreadParticipant.objects.filter(thread_id=self.thread_id, user_id=user_id).update(last_seen_at=timezone.now())

    @database_sync_to_async
    def _create_message(self, user_id, text, reply_to_id=None) -> Message:
        kwargs = {"thread_id": self.thread_id, "sender_id": user_id, "content": text}
        if reply_to_id:
            kwargs["reply_to_id"] = reply_to_id
        return Message.objects.create(**kwargs)

    @database_sync_to_async
    def _serialize_message(self, message_id) -> dict:
        m = Message.objects.select_related("sender", "thread", "reply_to").get(pk=message_id)
        return RoomMessageSerializer(m).data
