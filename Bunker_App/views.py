from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Lobby, LobbyInvitation, Game, PlayerCharacter, GameMessage, Vote
from django.http import JsonResponse
import json
from .charachteristics import *
from .utils import login_required_message, redirect_if_in_game
from users_App.models import Friend
from django.db.models import Q
import random
from .game_utils import generate_character

MAX_LOBBY_PARTICIPANTS = 9


@redirect_if_in_game
@login_required_message
def main_view(request):
    user_lobbies = request.user.joined_lobbies.all()
    pending_invitations = LobbyInvitation.objects.filter(invitee=request.user, status='pending').select_related('lobby', 'inviter')
    return render(request, 'main_page.html', {'user_lobbies': user_lobbies, 'pending_invitations': pending_invitations})


@redirect_if_in_game
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
            user_game = PlayerCharacter.objects.filter(player=request.user).first()
            if user_game:
                messages.error(request, 'You cannot join a new lobby while in an active game. Please exit your current game first.')
                return redirect('game_detail', game_id=user_game.game.id)

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

 
@redirect_if_in_game
@login_required_message
def create_party_view(request):
    current_lobby = request.user.joined_lobbies.first()
    
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



@redirect_if_in_game
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
            if action == 'update_settings' and request.user == lobby.creator:
                new_name = request.POST.get('name', '').strip()
                if new_name:
                    lobby.name = new_name
                max_p = request.POST.get('max_players', '')
                if max_p.isdigit():
                    lobby.max_players = max(2, min(9, int(max_p)))
                vis = request.POST.get('visibility', '')
                if vis in ('public', 'private', 'friends_only'):
                    lobby.visibility = vis
                lobby.save()
                messages.success(request, 'Lobby settings updated.')
            elif action == 'kick' and request.user == lobby.creator:
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
        
        # Check if user is in an active game
        user_game = PlayerCharacter.objects.filter(player=request.user).first()
        if user_game:
            messages.error(request, 'You cannot join a new lobby while in an active game. Please exit your current game first.')
            return redirect('game_detail', game_id=user_game.game.id)
        
        # Check if lobby still exists and user is not already in another lobby
        current_lobby = request.user.joined_lobbies.first()
        
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
        
        # Check if any participant is already in another game
        participants = list(lobby.participants.all())
        for participant in participants:
            existing_player_char = PlayerCharacter.objects.filter(player=participant).first()
            if existing_player_char:
                messages.error(request, f'{participant.username} is already in another game. All participants must exit their games before starting a new one.')
                return redirect('lobby_detail', lobby_id=lobby_id)

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
        all_characters = game.player_characters.all().select_related('player').order_by('id')
        
        # Get current player whose turn it is
        current_player = game.get_current_player()
        is_current_player_turn = (current_player and current_player.player == request.user)
        
        # Voting phase context
        has_voted = False
        votes_this_round = []
        votes_needed = 0
        votes_cast = 0
        if game.game_phase == 'voting':
            has_voted = Vote.objects.filter(game=game, voter=request.user, round_number=game.round_number).exists()
            votes_this_round = Vote.objects.filter(game=game, round_number=game.round_number).select_related('voter', 'target__player')
            votes_needed = game.player_characters.count()
            votes_cast = votes_this_round.count()

        # Get the last message ID (including system messages) to avoid duplicate notifications
        last_message = GameMessage.objects.filter(game=game).order_by('-id').first()
        last_message_id = last_message.id if last_message else 0
        should_delay_voting_panel = (
            game.game_phase == 'voting'
            and last_message is not None
            and last_message.text == '__VOTE_START__'
        )
        latest_reveal = None
        if should_delay_voting_panel:
            reveal_message = (
                GameMessage.objects
                .filter(game=game, text__startswith='__REVEAL__')
                .order_by('-id')
                .first()
            )
            if reveal_message:
                parts = reveal_message.text[len('__REVEAL__'):].split('|')
                if len(parts) >= 3:
                    latest_reveal = {
                        'id': reveal_message.id,
                        'player_id': reveal_message.player_id,
                        'username': parts[0],
                        'char_type': parts[1],
                        'value': parts[2],
                        'quality': parts[3] if len(parts) > 3 else 'good',
                    }

        return render(request, 'game_detail.html', {
            'game': game,
            'player_character': player_character,
            'all_characters': all_characters,
            'current_player': current_player,
            'is_current_player_turn': is_current_player_turn,
            'has_voted': has_voted,
            'votes_this_round': votes_this_round,
            'votes_needed': votes_cast,
            'votes_needed_total': votes_needed,
            'votes_cast': votes_cast,
            'last_message_id': last_message_id,
            'should_delay_voting_panel': should_delay_voting_panel,
            'latest_reveal': latest_reveal,
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


@login_required_message
def reveal_characteristic_view(request, game_id):
    """Reveal a chosen characteristic for the current player"""
    try:
        game = Game.objects.get(id=game_id)

        # Block reveals during voting phase
        if game.game_phase == 'voting':
            messages.error(request, 'Voting is in progress. Wait until the vote is complete.')
            return redirect('game_detail', game_id=game_id)

        # Get the current player's turn
        current_player = game.get_current_player()
        
        if current_player is None:
            messages.error(request, 'Invalid game state.')
            return redirect('game_detail', game_id=game_id)
        
        # Check if it's the current player's turn
        if current_player.player != request.user:
            messages.error(request, 'It is not your turn.')
            return redirect('game_detail', game_id=game_id)
        
        # Get the characteristic type to reveal
        char_type = request.POST.get('char_type')
        
        if not char_type:
            messages.error(request, 'Please select a characteristic to reveal.')
            return redirect('game_detail', game_id=game_id)
        
        # Validate that this characteristic exists for the player
        valid_char_types = [c[0] for c in current_player.get_all_revealable_characteristics()]
        if char_type not in valid_char_types:
            messages.error(request, 'Invalid characteristic.')
            return redirect('game_detail', game_id=game_id)
        
        # Check if already revealed
        if char_type in current_player.revealed_characteristics:
            messages.warning(request, 'That characteristic has already been revealed!')
            return redirect('game_detail', game_id=game_id)
        
        # Reveal the characteristic
        current_player.reveal_characteristic(char_type)
        
        # Find the value to show in message
        char_value = current_player.get_characteristic_value(char_type)
        
        messages.success(request, f'✨ Revealed: {char_type.replace("_", " ").title()} - {char_value}')
        
        # Post a system message to the game chat so everyone sees it
        quality_label = 'neutral'
        for c_type, c_value, c_quality in current_player.get_all_revealable_characteristics():
            if c_type == char_type:
                quality_label = c_quality
                break
        system_text = (
            f"__REVEAL__{request.user.username}|"
            f"{char_type.replace('_', ' ').title()}|"
            f"{char_value}|{quality_label}"
        )
        GameMessage.objects.create(game=game, player=request.user, text=system_text)

        # Move to next player's turn
        game.next_turn()

        # Check if every active player has revealed one characteristic this round
        active_players = list(game.player_characters.all())
        all_revealed_this_round = all(
            len(p.revealed_characteristics) >= game.round_number
            for p in active_players
        )
        anyone_has_unrevealed_characteristics = any(
            p.has_unrevealed_characteristics()
            for p in active_players
        )
        if all_revealed_this_round and len(active_players) > 1 and anyone_has_unrevealed_characteristics:
            game.game_phase = 'voting'
            game.save()
            GameMessage.objects.create(
                game=game,
                player=request.user,
                text='__VOTE_START__'
            )
        
        return redirect('game_detail', game_id=game_id)
    except Game.DoesNotExist:
        messages.error(request, 'Game does not exist.')
        return redirect('main')

@login_required_message
def chat_send_view(request, game_id):
    """Send a chat message in a game (AJAX POST)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        game = Game.objects.get(id=game_id)
        # Only participants can chat
        if not game.player_characters.filter(player=request.user).exists():
            return JsonResponse({'error': 'Not a participant'}, status=403)
        try:
            body = json.loads(request.body)
            text = body.get('text', '').strip()
        except (json.JSONDecodeError, AttributeError):
            text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'Empty message'}, status=400)
        if len(text) > 500:
            return JsonResponse({'error': 'Message too long'}, status=400)
        msg = GameMessage.objects.create(game=game, player=request.user, text=text)
        avatar_url = ''
        if hasattr(request.user, 'profile') and request.user.profile.avatar:
            avatar_url = request.user.profile.avatar.url
        return JsonResponse({
            'id': msg.id,
            'username': request.user.username,
            'text': msg.text,
            'avatar_url': avatar_url,
            'is_you': True,
            'time': msg.created_at.strftime('%H:%M'),
        })
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)


@login_required_message
def chat_poll_view(request, game_id):
    """Poll for new messages since a given message id (AJAX GET)"""
    try:
        game = Game.objects.get(id=game_id)
        if not game.player_characters.filter(player=request.user).exists():
            return JsonResponse({'error': 'Not a participant'}, status=403)
        since_id = int(request.GET.get('since', 0))
        msgs = GameMessage.objects.filter(game=game, id__gt=since_id).order_by('id').select_related('player__profile')
        data = []
        for msg in msgs:
            is_system = msg.text.startswith('__REVEAL__') or msg.text.startswith('__VOTE') or msg.text.startswith('__EXPELLED__') or msg.text.startswith('__TIE__')
            avatar_url = ''
            if hasattr(msg.player, 'profile') and msg.player.profile.avatar:
                avatar_url = msg.player.profile.avatar.url
            data.append({
                'id': msg.id,
                'username': msg.player.username,
                'text': msg.text,
                'avatar_url': avatar_url,
                'is_you': msg.player == request.user,
                'is_system': is_system,
                'time': msg.created_at.strftime('%H:%M'),
            })
        return JsonResponse({'messages': data})
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)


@login_required_message
def vote_view(request, game_id):
    """Cast a vote to expel a player"""
    if request.method != 'POST':
        return redirect('game_detail', game_id=game_id)
    try:
        game = Game.objects.get(id=game_id)

        if game.game_phase != 'voting':
            messages.error(request, 'Not in voting phase.')
            return redirect('game_detail', game_id=game_id)

        # Must be a participant
        if not game.player_characters.filter(player=request.user).exists():
            messages.error(request, 'You are not in this game.')
            return redirect('main')

        # Already voted this round?
        if Vote.objects.filter(game=game, voter=request.user, round_number=game.round_number).exists():
            messages.warning(request, 'You have already voted this round.')
            return redirect('game_detail', game_id=game_id)

        target_id = request.POST.get('target_id')
        try:
            target_char = game.player_characters.get(id=target_id)
        except PlayerCharacter.DoesNotExist:
            messages.error(request, 'Invalid vote target.')
            return redirect('game_detail', game_id=game_id)

        # Cannot vote for yourself
        if target_char.player == request.user:
            messages.error(request, 'You cannot vote for yourself.')
            return redirect('game_detail', game_id=game_id)

        Vote.objects.create(
            game=game,
            voter=request.user,
            target=target_char,
            round_number=game.round_number
        )

        GameMessage.objects.create(
            game=game,
            player=request.user,
            text=f'__VOTED__{request.user.username}'
        )

        # Check if all active players have voted
        active_count = game.player_characters.count()
        votes_cast = Vote.objects.filter(game=game, round_number=game.round_number).count()

        if votes_cast >= active_count:
            # Tally votes and expel the most-voted player
            from django.db.models import Count
            tally = (Vote.objects
                     .filter(game=game, round_number=game.round_number)
                     .values('target')
                     .annotate(count=Count('id'))
                     .order_by('-count'))

            top_votes = tally[0]['count']
            top_targets = [t for t in tally if t['count'] == top_votes]

            if len(top_targets) == 1:
                # Clear winner — expel them
                expelled_char = game.player_characters.get(id=top_targets[0]['target'])
                expelled_name = expelled_char.player.username
                expelled_char.delete()
                GameMessage.objects.create(
                    game=game,
                    player=request.user,
                    text=f'__EXPELLED__{expelled_name}'
                )
            else:
                # Tie — no one expelled this round
                GameMessage.objects.create(
                    game=game,
                    player=request.user,
                    text='__TIE__'
                )

            # Move to next round revealing phase
            game.game_phase = 'revealing'
            game.round_number += 1
            # Reset turn index to 0 for the next round
            game.current_turn_index = 0
            game.save()

        messages.success(request, 'Your vote has been cast.')
        return redirect('game_detail', game_id=game_id)

    except Game.DoesNotExist:
        messages.error(request, 'Game does not exist.')
        return redirect('main')


@login_required_message
def lobby_chat_send_view(request, lobby_id):
    """Send a chat message in a lobby (AJAX POST)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        lobby = Lobby.objects.get(id=lobby_id)
        if request.user not in lobby.participants.all():
            return JsonResponse({'error': 'Not a participant'}, status=403)
        try:
            body = json.loads(request.body)
            text = body.get('text', '').strip()
        except (json.JSONDecodeError, AttributeError):
            text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'Empty message'}, status=400)
        if len(text) > 500:
            return JsonResponse({'error': 'Message too long'}, status=400)
        from .models import LobbyMessage
        msg = LobbyMessage.objects.create(lobby=lobby, player=request.user, text=text)
        avatar_url = ''
        if hasattr(request.user, 'profile') and request.user.profile.avatar:
            avatar_url = request.user.profile.avatar.url
        return JsonResponse({
            'id': msg.id,
            'username': request.user.username,
            'text': msg.text,
            'avatar_url': avatar_url,
            'is_you': True,
            'time': msg.created_at.strftime('%H:%M'),
        })
    except Lobby.DoesNotExist:
        return JsonResponse({'error': 'Lobby not found'}, status=404)


@login_required_message
def lobby_chat_poll_view(request, lobby_id):
    """Poll for new lobby messages since a given message id (AJAX GET)"""
    try:
        lobby = Lobby.objects.get(id=lobby_id)
        if request.user not in lobby.participants.all():
            return JsonResponse({'error': 'Not a participant'}, status=403)
        since_id = int(request.GET.get('since', 0))
        from .models import LobbyMessage
        msgs = LobbyMessage.objects.filter(lobby=lobby, id__gt=since_id).order_by('id').select_related('player__profile')
        data = []
        for msg in msgs:
            avatar_url = ''
            if hasattr(msg.player, 'profile') and msg.player.profile.avatar:
                avatar_url = msg.player.profile.avatar.url
            data.append({
                'id': msg.id,
                'username': msg.player.username,
                'text': msg.text,
                'avatar_url': avatar_url,
                'is_you': msg.player == request.user,
                'time': msg.created_at.strftime('%H:%M'),
            })
        return JsonResponse({'messages': data})
    except Lobby.DoesNotExist:
        return JsonResponse({'error': 'Lobby not found'}, status=404)