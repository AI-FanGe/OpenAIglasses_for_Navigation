from django.urls import path
from .views import CustomAuthToken, UserInfoView

urlpatterns = [
    path('login/', CustomAuthToken.as_view(), name='api_login'),
    path('me/', UserInfoView.as_view(), name='api_me'),
]
