from django.contrib import admin
from .models import Lobby, Profile, Friend, LobbyInvitation

admin.site.register(Lobby)
admin.site.register(Profile)
admin.site.register(Friend)
admin.site.register(LobbyInvitation)
