from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True)
    # Add other fields like avatar if needed

    def __str__(self):
        return f"{self.user.username}'s profile"

class Friend(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    from_user = models.ForeignKey(User, related_name='friend_requests_sent', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='friend_requests_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"

class LobbyInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    lobby = models.ForeignKey('Lobby', on_delete=models.CASCADE)
    inviter = models.ForeignKey(User, related_name='invitations_sent', on_delete=models.CASCADE)
    invitee = models.ForeignKey(User, related_name='invitations_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lobby', 'invitee')

    def __str__(self):
        return f"{self.inviter} invited {self.invitee} to {self.lobby}"

class Lobby(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_game', 'In Game'),
        ('finished', 'Finished'),
    ]
    name = models.CharField(max_length=255)
    code = models.PositiveIntegerField(unique=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_lobbies')
    participants = models.ManyToManyField(User, related_name='joined_lobbies')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')

    def __str__(self):
        return f"{self.name} ({self.code})"


class Game(models.Model):
    lobby = models.OneToOneField(Lobby, on_delete=models.CASCADE, related_name='game')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Game for {self.lobby.name}"


class PlayerCharacter(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='player_characters')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_characters')
    age = models.IntegerField()
    gender = models.CharField(max_length=20)
    height = models.CharField(max_length=20)
    profession = models.CharField(max_length=100)
    hobby = models.CharField(max_length=100)
    health = models.CharField(max_length=100)
    item = models.CharField(max_length=100)
    special_trait = models.CharField(max_length=200)
    phobia = models.CharField(max_length=100)
    characteristics = models.JSONField(default=list)  # Store all characteristics including bad ones

    def __str__(self):
        return f"{self.player.username}'s character in {self.game.lobby.name}"
 