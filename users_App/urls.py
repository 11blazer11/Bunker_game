from django.urls import path
from .views import (
    edit_profile_view, public_profile_view, register_view, login_view, logout_view, account_view,
    friends_view, accept_friend_view, decline_friend_view, activate,
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('account/', account_view, name='account'),
    path('account/edit/', edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/', public_profile_view, name='public_profile'),
    path('friends/', friends_view, name='friends'),
    path('accept_friend/<int:friend_id>/', accept_friend_view, name='accept_friend'),
    path('decline_friend/<int:friend_id>/', decline_friend_view, name='decline_friend'),
    path('activate/<token>/', activate, name='activate'),
]
