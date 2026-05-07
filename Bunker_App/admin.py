from django.contrib import admin
from .models import LobbyInvitation, Lobby, Game, PlayerCharacter

admin.site.register(LobbyInvitation)
admin.site.register(Lobby)
admin.site.register(Game)
admin.site.register(PlayerCharacter)
