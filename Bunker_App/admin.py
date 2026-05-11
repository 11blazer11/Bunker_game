from django.contrib import admin
from .models import LobbyInvitation, Lobby, Game, PlayerCharacter

admin.site.register(LobbyInvitation)
admin.site.register(Lobby)


class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'lobby', 'started_at', 'finished_at')
    list_filter = ('started_at', 'finished_at')
    readonly_fields = ('id', 'started_at')


admin.site.register(Game, GameAdmin)
admin.site.register(PlayerCharacter)
