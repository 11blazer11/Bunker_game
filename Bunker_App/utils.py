from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def login_required_message(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Try to login to access this page")
            return redirect('login')  # redirect to your login page
        return view_func(request, *args, **kwargs)
    return wrapper


def redirect_if_in_game(view_func):
    """Redirect user to their active game if they're currently in one"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Check if user has an active game
            from .models import PlayerCharacter
            try:
                player_character = PlayerCharacter.objects.filter(
                    player=request.user
                ).select_related('game').first()
                
                if player_character:
                    # User is in an active game, redirect them to it
                    return redirect('game_detail', game_id=player_character.game.id)
            except:
                pass
        
        return view_func(request, *args, **kwargs)
    return wrapper