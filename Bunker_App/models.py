from django.db import models
from django.contrib.auth.models import User

class Lobby(models.Model):
    name = models.CharField(max_length=255)
    code = models.PositiveIntegerField(unique=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_lobbies')
    participants = models.ManyToManyField(User, related_name='joined_lobbies')
 