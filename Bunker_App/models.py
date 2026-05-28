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
    id = models.AutoField(primary_key=True)
    lobby = models.ForeignKey(Lobby, on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    current_turn_index = models.IntegerField(default=0)  # Index of player whose turn it is

    def __str__(self):
        if self.lobby:
            return f"Game #{self.id} - {self.lobby.name}"
        return f"Game #{self.id} (no lobby)"
    
    def get_current_player(self):
        """Get the player whose turn it is"""
        players = self.player_characters.all().order_by('id')
        if players.exists() and self.current_turn_index < len(players):
            return list(players)[self.current_turn_index]
        return None
    
    def next_turn(self):
        """Move to the next player's turn"""
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
    characteristics = models.JSONField(default=list)  # Store all characteristics including bad ones
    revealed_characteristics = models.JSONField(default=list)  # Track which characteristics have been revealed

    def __str__(self):
        return f"{self.player.username}'s character in {self.game.lobby.name}"
    
    def reveal_characteristic(self, char_type):
        """Reveal a specific characteristic for this player"""
        if char_type not in self.revealed_characteristics:
            self.revealed_characteristics.append(char_type)
            self.save()
            return True
        return False  # Already revealed or invalid
    
    def get_unrevealed_characteristics(self):
        """Get the characteristics that have NOT been revealed for this player"""
        unrevealed = []
        for char_type, char_value, quality in self.characteristics:
            if char_type not in self.revealed_characteristics:
                unrevealed.append((char_type, char_value, quality))
        return unrevealed
    
    def get_revealed_characteristics(self):
        """Get the characteristics that have been revealed for this player"""
        revealed = []
        for char_type, char_value, quality in self.characteristics:
            if char_type in self.revealed_characteristics:
                revealed.append((char_type, char_value, quality))
        return revealed