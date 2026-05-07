from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Lobby, LobbyInvitation, Game, PlayerCharacter
from .charachteristics import *
from .utils import login_required_message
from users_App.models import Friend
from django.db.models import Q
import random
from .game_utils import generate_character

MAX_LOBBY_PARTICIPANTS = 9


@login_required_message
def main_view(request):
    user_lobbies = request.user.joined_lobbies.all()
    pending_invitations = LobbyInvitation.objects.filter(invitee=request.user, status='pending').select_related('lobby', 'inviter')
    return render(request, 'main_page.html', {'user_lobbies': user_lobbies, 'pending_invitations': pending_invitations})


@login_required_message
def join_party_view(request):
    if request.method == 'POST':
        code = request.POST.get('party_code')
        try:
            lobby = Lobby.objects.get(code=code)
            current_lobby = request.user.joined_lobbies.exclude(id=lobby.id).first()

            if request.user in lobby.participants.all():
                messages.warning(request, 'You are already in this lobby.')
                return redirect('lobby_detail', lobby_id=lobby.id)

            # Check if user is in an active game
            if current_lobby and current_lobby.status in ['in_game', 'finished']:
                messages.error(request, 'You cannot join a new lobby while in an active or finished game.')
                return redirect('lobby_detail', lobby_id=current_lobby.id)

            if current_lobby and request.POST.get('confirm') != 'true':
                return render(request, 'join_party_confirm.html', {
                    'current_lobby': current_lobby,
                    'new_lobby': lobby,
                    'party_code': code,
                })

            if lobby.participants.count() >= MAX_LOBBY_PARTICIPANTS:
                messages.error(request, f'Lobby is full. Maximum {MAX_LOBBY_PARTICIPANTS} participants allowed.')
                return redirect('join_party')

            if current_lobby:
                if current_lobby.status == 'waiting':
                    if current_lobby.creator == request.user:
                        current_lobby.delete()
                    else:
                        current_lobby.participants.remove(request.user)
                else:
                    messages.error(request, 'Cannot leave an active game.')
                    return redirect('lobby_detail', lobby_id=current_lobby.id)

            request.user.joined_lobbies.clear()
            lobby.participants.add(request.user)
            messages.success(request, f'Joined lobby "{lobby.name}"')
            return redirect('lobby_detail', lobby_id=lobby.id)
        except Lobby.DoesNotExist:
            messages.error(request, 'Lobby with this code does not exist.')
    return render(request, 'join_party.html')

 
@login_required_message
def create_party_view(request):
    current_lobby = request.user.joined_lobbies.first()
    
    # Check if user is in an active game
    if current_lobby and current_lobby.status in ['in_game', 'finished']:
        messages.error(request, 'You cannot create a new lobby while in an active or finished game. You must exit the game first.')
        return redirect('lobby_detail', lobby_id=current_lobby.id)
    
    if current_lobby and request.method != 'POST':
        return render(request, 'create_party_confirm.html', {'current_lobby': current_lobby})

    if current_lobby:
        if current_lobby.status == 'waiting':
            if current_lobby.creator == request.user:
                current_lobby.delete()
            else:
                current_lobby.participants.remove(request.user)

    code = random.randint(100000, 999999)
    while Lobby.objects.filter(code=code).exists():
        code = random.randint(100000, 999999)
    lobby_name = f"{request.user.username}'s lobby"
    lobby = Lobby.objects.create(name=lobby_name, code=code, creator=request.user)
    lobby.participants.add(request.user)
    return redirect('lobby_detail', lobby_id=lobby.id)



@login_required_message
def find_party_view(request):
    query = request.GET.get('search_query')
    if query:
        lobbies = Lobby.objects.filter(name__icontains=query)
    else:
        lobbies = Lobby.objects.exclude(participants=request.user)
    return render(request, 'find_party.html', {'lobbies': lobbies, 'query': query})


@login_required_message
def lobby_detail_view(request, lobby_id):
    try:
        lobby = Lobby.objects.get(id=lobby_id)
        if request.user not in lobby.participants.all():
            messages.error(request, 'You are not a participant in this lobby.')
            return redirect('main')
        
        # Get friends list
        friends = Friend.objects.filter(
            (Q(from_user=request.user) | Q(to_user=request.user)) & Q(status='accepted')
        ).select_related('from_user', 'to_user')
        
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'kick' and request.user == lobby.creator:
                user_id = request.POST.get('user_id')
                try:
                    user_to_kick = User.objects.get(id=user_id)
                    if user_to_kick != lobby.creator and user_to_kick in lobby.participants.all():
                        lobby.participants.remove(user_to_kick)
                        messages.success(request, f'Kicked {user_to_kick.username} from the lobby.')
                    else:
                        messages.error(request, 'Cannot kick this user.')
                except User.DoesNotExist:
                    messages.error(request, 'User not found.')
            elif action == 'delete' and request.user == lobby.creator:
                lobby.delete()
                messages.success(request, 'Lobby deleted successfully.')
                return redirect('main')
            elif action == 'leave' and request.user in lobby.participants.all():
                if request.user == lobby.creator:
                    next_creator = lobby.participants.exclude(id=request.user.id).order_by('id').first()
                    if next_creator:
                        lobby.creator = next_creator
                        lobby.save()
                        lobby.participants.remove(request.user)
                        messages.success(request, f'You left the lobby. {next_creator.username} is now the creator.')
                        return redirect('main')
                    else:
                        lobby.delete()
                        messages.success(request, 'Lobby deleted because there were no other participants.')
                        return redirect('main')
                else:
                    lobby.participants.remove(request.user)
                    messages.success(request, 'You have left the lobby.')
                    return redirect('main')
        
        return render(request, 'lobby_detail.html', {'lobby': lobby, 'friends': friends})
    except Lobby.DoesNotExist:
        messages.error(request, 'Lobby does not exist.')
        return redirect('main')


@login_required_message
def send_lobby_invitation_view(request, lobby_id):
    """Send a lobby invitation to a friend"""
    if request.method == 'POST':
        try:
            lobby = Lobby.objects.get(id=lobby_id)
            if request.user not in lobby.participants.all():
                messages.error(request, 'You are not a participant in this lobby.')
                return redirect('main')
            
            friend_id = request.POST.get('friend_id')
            try:
                friend_user = User.objects.get(id=friend_id)
                
                # Check if they are friends
                friendship = Friend.objects.filter(
                    (Q(from_user=request.user, to_user=friend_user) | Q(from_user=friend_user, to_user=request.user))
                    & Q(status='accepted')
                ).first()
                
                if not friendship:
                    messages.error(request, 'You can only invite accepted friends.')
                    return redirect('lobby_detail', lobby_id=lobby_id)
                
                # Check if invitation already exists
                existing = LobbyInvitation.objects.filter(
                    lobby=lobby,
                    invitee=friend_user,
                    status='pending'
                ).first()
                
                if existing:
                    messages.warning(request, f'You have already sent an invitation to {friend_user.username}.')
                    return redirect('lobby_detail', lobby_id=lobby_id)
                
                # Create invitation
                LobbyInvitation.objects.create(
                    lobby=lobby,
                    inviter=request.user,
                    invitee=friend_user
                )
                messages.success(request, f'Invitation sent to {friend_user.username}')
                return redirect('lobby_detail', lobby_id=lobby_id)
            except User.DoesNotExist:
                messages.error(request, 'Friend not found.')
                return redirect('lobby_detail', lobby_id=lobby_id)
        except Lobby.DoesNotExist:
            messages.error(request, 'Lobby does not exist.')
            return redirect('main')
    return redirect('lobby_detail', lobby_id=lobby_id)


@login_required_message
def accept_lobby_invitation_view(request, invitation_id):
    """Accept a lobby invitation"""
    try:
        invitation = LobbyInvitation.objects.get(id=invitation_id, invitee=request.user, status='pending')
        lobby = invitation.lobby
        
        # Check if lobby still exists and user is not already in another lobby
        current_lobby = request.user.joined_lobbies.first()
        
        # Check if user is in an active game
        if current_lobby and current_lobby != lobby and current_lobby.status in ['in_game', 'finished']:
            messages.error(request, 'You cannot join a new lobby while in an active or finished game. You must exit the game first.')
            return redirect('lobby_detail', lobby_id=current_lobby.id)
        
        if current_lobby and current_lobby != lobby:
            if current_lobby.status == 'waiting':
                if current_lobby.creator == request.user:
                    current_lobby.delete()
                else:
                    current_lobby.participants.remove(request.user)
        
        # Check if lobby is full
        if lobby.participants.count() >= MAX_LOBBY_PARTICIPANTS:
            messages.error(request, f'Lobby is full. Maximum {MAX_LOBBY_PARTICIPANTS} participants allowed.')
            invitation.status = 'declined'
            invitation.save()
            return redirect('main')
        
        # Add user to lobby
        lobby.participants.add(request.user)
        invitation.status = 'accepted'
        invitation.save()
        messages.success(request, f'Joined lobby "{lobby.name}"')
        return redirect('lobby_detail', lobby_id=lobby.id)
    except LobbyInvitation.DoesNotExist:
        messages.error(request, 'Invitation not found.')
        return redirect('main')


@login_required_message
def decline_lobby_invitation_view(request, invitation_id):
    """Decline a lobby invitation"""
    try:
        invitation = LobbyInvitation.objects.get(id=invitation_id, invitee=request.user, status='pending')
        invitation.status = 'declined'
        invitation.save()
        messages.success(request, f'Declined invitation to {invitation.lobby.name}')
    except LobbyInvitation.DoesNotExist:
        messages.error(request, 'Invitation not found.')
    return redirect('main')


@login_required_message
def start_game_view(request, lobby_id):
    """Start a game for the lobby - only creator can start"""
    try:
        lobby = Lobby.objects.get(id=lobby_id)
        if request.user != lobby.creator:
            messages.error(request, 'Only the lobby creator can start the game.')
            return redirect('lobby_detail', lobby_id=lobby_id)
        
        if lobby.status != 'waiting':
            messages.error(request, 'Game already started or finished.')
            return redirect('lobby_detail', lobby_id=lobby_id)
        
        # Check if game already exists for this lobby
        existing_game = Game.objects.filter(lobby=lobby).first()
        if existing_game:
            messages.info(request, 'Game already started.')
            return redirect('game_detail', game_id=existing_game.id)
        
        # Snapshot participants BEFORE deleting the lobby
        participants = list(lobby.participants.all())

        # Create game and assign characters to all participants
        game = Game.objects.create(lobby=lobby)
        
        for participant in participants:
            character = generate_character()
            PlayerCharacter.objects.create(
                game=game,
                player=participant,
                age=character['age'],
                gender=character['gender'],
                height=character['height'],
                profession=character['profession'],
                hobby=character['hobby'],
                health=character['health'],
                item=character['item'],
                special_trait=character['special_trait'],
                phobia=character['phobia'],
                characteristics=character['all_characteristics']
            )
        
        # Delete the lobby completely now that the game has been created
        lobby.delete()
        
        messages.success(request, 'Game started! Characters have been assigned.')
        return redirect('game_detail', game_id=game.id)
    except Lobby.DoesNotExist:
        messages.error(request, 'Lobby does not exist.')
        return redirect('main')


@login_required_message
def game_detail_view(request, game_id):
    """Display the game and character details"""
    try:
        game = Game.objects.get(id=game_id)
        
        # Get the current player's character - this is the real permission check
        # If they have a character in the game, they can view it
        try:
            player_character = game.player_characters.get(player=request.user)
        except PlayerCharacter.DoesNotExist:
            messages.error(request, 'You are not a participant in this game.')
            return redirect('main')
        
        # Get all characters for display
        all_characters = game.player_characters.all().select_related('player')
        
        return render(request, 'game_detail.html', {
            'game': game,
            'player_character': player_character,
            'all_characters': all_characters,
        })
    
    except Game.DoesNotExist:
        messages.error(request, 'Game does not exist.')
        return redirect('main')
    except PlayerCharacter.DoesNotExist:
        messages.error(request, 'Your character not found in this game.')
        return redirect('main')


@login_required_message
def exit_game_view(request, game_id):
    """Exit the current game"""
    try:
        game = Game.objects.get(id=game_id)
        
        # Find and delete the player's character
        try:
            player_character = game.player_characters.get(player=request.user)
            player_character.delete()
            messages.success(request, 'You have exited the game.')
        except PlayerCharacter.DoesNotExist:
            messages.warning(request, 'You are not in this game.')
            return redirect('main')
        
        # If no players remain, delete the game entirely
        if game.player_characters.count() == 0:
            game.delete()
        
        return redirect('main')
    except Game.DoesNotExist:
        messages.error(request, 'Game does not exist.')
        return redirect('main')