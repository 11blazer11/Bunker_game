from django.db import models
from django.contrib.auth.models import User

class Lobby(models.Model):
    name = models.CharField(max_length=255)
    code = models.PositiveIntegerField(unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='User')
