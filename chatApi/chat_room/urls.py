from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ThreadViewSet, MessageListCreateView

router = DefaultRouter()
router.register(r"threads", ThreadViewSet, basename="thread")

urlpatterns = [
    path("", include(router.urls)),
    path("threads/<int:thread_id>/messages/", MessageListCreateView.as_view(), name="thread-messages"),
]
