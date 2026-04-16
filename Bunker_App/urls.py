from django.urls import path
from .views import register_view, login_view, logout_view, main_view, account_view, friends_view, accept_friend_view, decline_friend_view, create_party_view, find_party_view, join_party_view, activate, lobby_detail_view

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', main_view, name='main'),
    path('account/', account_view, name='account'),
    path('friends/', friends_view, name='friends'),
    path('accept_friend/<int:friend_id>/', accept_friend_view, name='accept_friend'),
    path('decline_friend/<int:friend_id>/', decline_friend_view, name='decline_friend'),
    path('create/', create_party_view, name='create_party'),
    path('find/', find_party_view, name='find_party'),
    path('join/', join_party_view, name='join_party'),
    path('lobby/<int:lobby_id>/', lobby_detail_view, name='lobby_detail'),

    path('activate/<token>/', activate, name='activate'),
] 