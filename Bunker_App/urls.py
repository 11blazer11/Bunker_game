from django.urls import path
from .views import (
    main_view, create_party_view, find_party_view, join_party_view,
    lobby_detail_view, send_lobby_invitation_view, accept_lobby_invitation_view,
    decline_lobby_invitation_view, start_game_view, game_detail_view, exit_game_view
)

urlpatterns = [
    path('', main_view, name='main'),
    path('create/', create_party_view, name='create_party'),
    path('find/', find_party_view, name='find_party'),
    path('join/', join_party_view, name='join_party'),
    path('lobby/<int:lobby_id>/', lobby_detail_view, name='lobby_detail'),
    path('lobby/<int:lobby_id>/start/', start_game_view, name='start_game'),
    path('lobby/<int:lobby_id>/invite/', send_lobby_invitation_view, name='send_lobby_invitation'),
    path('invitation/<int:invitation_id>/accept/', accept_lobby_invitation_view, name='accept_lobby_invitation'),
    path('invitation/<int:invitation_id>/decline/', decline_lobby_invitation_view, name='decline_lobby_invitation'),
    path('game/<int:game_id>/', game_detail_view, name='game_detail'),
    path('game/<int:game_id>/exit/', exit_game_view, name='exit_game'),
]
