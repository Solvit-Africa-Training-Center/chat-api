from django.urls import re_path
from .consumers import ThreadConsumer

websocket_urlpatterns = [
    re_path(r'^ws/threads/(?P<thread_id>[0-9]+)/$', ThreadConsumer.as_asgi()),
]
