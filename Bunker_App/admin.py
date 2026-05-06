from django.contrib import admin
from .models import Profile, Friend, LobbyInvitation, Lobby, Game, PlayerCharacter

admin.site.register(Profile)
admin.site.register(Friend)
admin.site.register(LobbyInvitation)
admin.site.register(Lobby)
admin.site.register(Game)
admin.site.register(PlayerCharacter)