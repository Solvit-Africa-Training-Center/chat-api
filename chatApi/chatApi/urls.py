from django.contrib import admin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path, include
from accounts.views import RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('api/register', RegisterView.as_view(), name='register'),
    path('',include('accounts.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
