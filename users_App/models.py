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
