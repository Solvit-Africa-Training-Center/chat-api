from django.urls import path, include
from .views import RegisterView
from rest_framework import routers

route = routers.DefaultRouter()
route.register('register', RegisterView, basename="register")

urlpatterns = [
    path('', include(route.urls)),
    # path('', RegisterView.as_view()),
]
