from django.db import models
from django.contrib.auth.models import User

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

class Game(models.Model):
    id = models.AutoField(primary_key=True)
    lobby = models.ForeignKey(Lobby, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    current_turn_index = models.IntegerField(default=0)
    game_phase = models.CharField(max_length=20, default='revealing')  # 'revealing' or 'voting'
    round_number = models.IntegerField(default=1)

    def get_current_player(self):
        players = self.player_characters.all().order_by('id')
        if players.exists() and self.current_turn_index < len(players):
            return list(players)[self.current_turn_index]
        return None

    def next_turn(self):
        player_count = self.player_characters.count()
        if player_count > 0:
            self.current_turn_index = (self.current_turn_index + 1) % player_count
            self.save()

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
    characteristics = models.JSONField(default=list)
    revealed_characteristics = models.JSONField(default=list)

    def reveal_characteristic(self, char_type):
        if char_type not in self.revealed_characteristics:
            self.revealed_characteristics.append(char_type)
            self.save()
            return True
        return False

    def get_unrevealed_characteristics(self):
        unrevealed = []
        for char_type, char_value, quality in self.characteristics:
            if char_type not in self.revealed_characteristics:
                unrevealed.append((char_type, char_value, quality))
        return unrevealed

    def get_revealed_characteristics(self):
        revealed = []
        for char_type, char_value, quality in self.characteristics:
            if char_type in self.revealed_characteristics:
                revealed.append((char_type, char_value, quality))
        return revealed

# NEW: Chat message model
class GameMessage(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='messages')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_messages')
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.player.username}: {self.text[:40]}"


class Vote(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes_cast')
    target = models.ForeignKey(PlayerCharacter, on_delete=models.CASCADE, related_name='votes_received')
    round_number = models.IntegerField()

    class Meta:
        unique_together = ('game', 'voter', 'round_number')  # one vote per player per round

    def __str__(self):
        return f"{self.voter.username} voted for {self.target.player.username} in round {self.round_number}"


class LobbyMessage(models.Model):
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='messages')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lobby_messages')
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.player.username} in {self.lobby.name}: {self.text[:40]}"