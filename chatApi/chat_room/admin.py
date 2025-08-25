from django.contrib import admin
from .models import Room, RoomParticipant, Message
# Register your models here.

admin.site.register(Room)
admin.site.register(RoomParticipant)
admin.site.register(Message)
