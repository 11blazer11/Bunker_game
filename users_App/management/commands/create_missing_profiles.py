from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users_App.models import Profile


class Command(BaseCommand):
    help = 'Create missing profiles for existing users'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(profile__isnull=True)
        count = 0
        
        for user in users_without_profile:
            Profile.objects.create(user=user)
            count += 1
        
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {count} missing profile(s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles')
            )
