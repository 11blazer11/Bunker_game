from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.signing import dumps, loads, BadSignature, SignatureExpired
from .forms import CustomUserCreationForm
from .models import Lobby, Friend, LobbyInvitation
from .charachteristics import *
from django.contrib import messages
from .utils import login_required_message
from django.db.models import Q
import random
from django.core.mail import EmailMultiAlternatives

MAX_LOBBY_PARTICIPANTS = 9

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage

def activate(request, token):
    User = get_user_model()
    try:
        payload = loads(token, salt=ACTIVATION_SALT, max_age=ACTIVATION_MAX_AGE)
    except SignatureExpired:
        messages.error(request, 'Activation link has expired. Please register again.')
        return redirect('register')
    except BadSignature:
        messages.error(request, 'Activation link is invalid!')
        return redirect('register')

    username = payload.get('username')
    email = payload.get('email')
    password = payload.get('password')

    if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
        messages.warning(request, 'This account has already been activated or email is already registered.')
        return redirect('login')

    user = User(username=username, email=email, password=password, is_active=True)
    user.save()
    messages.success(request, 'Thank you for your email confirmation. You can now login to your account.')
    return redirect('login')

ACTIVATION_SALT = 'activate-account'
ACTIVATION_MAX_AGE = 60 * 60 * 24  


def send_verification_email(request, username, email_address, password):
    mail_subject = 'Activate your user account'
    payload = {
        'username': username,
        'email': email_address,
        'password': make_password(password),
    }
    token = dumps(payload, salt=ACTIVATION_SALT)
    
    context = {
        'user': username,
        'domain': get_current_site(request).domain,
        'token': token,
        'protocol': 'https' if request.is_secure() else 'http',
    }

    html_content = render_to_string('verify_email.html', context)
    text_content = f"Hey {username}, activate your account here: {context['protocol']}://{context['domain']}/activate/{token}/"

    email = EmailMultiAlternatives(mail_subject, text_content, to=[email_address])
    email.attach_alternative(html_content, "text/html")

    if email.send():
        messages.success(request, f'Please confirm your email address to complete the registration. We have sent you an email to {email_address}')
        return True
    else:
        messages.error(request, f'Problem sending email to {email_address}, check if you typed it correctly.')
        return False
  

def register_view(request):
    form = CustomUserCreationForm(request.POST)
    if request.method == "POST":
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            if send_verification_email(request, username, email, password):
                return redirect('login')

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            user_obj = None

        if user_obj:
            if user_obj.is_active:
                user = authenticate(request, username=user_obj.username, password=password)
                if user:
                    login(request, user)
                    return redirect('main')  
                else:
                    messages.error(request, "Invalid password!")
                    return redirect('login')
            else:
                messages.warning(request, "Your account is inactive. Please check your email for the activation link.")
                return redirect('login')
        else:
            messages.error(request, "No account found with this email!")
            return redirect('login')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required_message
def main_view(request):
    user_lobbies = request.user.joined_lobbies.all()
    pending_invitations = LobbyInvitation.objects.filter(invitee=request.user, status='pending').select_related('lobby', 'inviter')
    return render(request, 'main_page.html', {'user_lobbies': user_lobbies, 'pending_invitations': pending_invitations})


@login_required_message
def account_view(request):
    return render(request, 'account.html')


@login_required_message
def friends_view(request):
    from .models import Friend, Profile
    friends = Friend.objects.filter(
        (Q(from_user=request.user) | Q(to_user=request.user)) & Q(status='accepted')
    ).select_related('from_user', 'to_user')
    
    friend_requests = Friend.objects.filter(to_user=request.user, status='pending').select_related('from_user')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        if username:
            try:
                friend_user = User.objects.get(username=username)
                if friend_user != request.user:
                    # Check if already friends or request exists
                    existing = Friend.objects.filter(
                        (Q(from_user=request.user, to_user=friend_user) | Q(from_user=friend_user, to_user=request.user))
                    ).first()
                    if not existing:
                        Friend.objects.create(from_user=request.user, to_user=friend_user)
                        messages.success(request, f'Friend request sent to {username}')
                    else:
                        messages.warning(request, 'Friend request already exists or you are already friends.')
                else:
                    messages.error(request, 'You cannot add yourself as a friend.')
            except User.DoesNotExist:
                messages.error(request, f'User {username} not found.')
    
    return render(request, 'friends.html', {
        'friends': friends,
        'friend_requests': friend_requests,
    })


@login_required_message
def accept_friend_view(request, friend_id):
    try:
        friend_request = Friend.objects.get(id=friend_id, to_user=request.user, status='pending')
        friend_request.status = 'accepted'
        friend_request.save()
        messages.success(request, f'You are now friends with {friend_request.from_user.username}')
    except Friend.DoesNotExist:
        messages.error(request, 'Friend request not found.')
    return redirect('friends')


@login_required_message
def decline_friend_view(request, friend_id):
    try:
        friend_request = Friend.objects.get(id=friend_id, to_user=request.user, status='pending')
        friend_request.status = 'declined'
        friend_request.save()
        messages.success(request, f'Friend request from {friend_request.from_user.username} declined.')
    except Friend.DoesNotExist:
        messages.error(request, 'Friend request not found.')
    return redirect('friends')


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
                if current_lobby.creator == request.user:
                    current_lobby.delete()
                else:
                    current_lobby.participants.remove(request.user)

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
    if current_lobby and request.method != 'POST':
        return render(request, 'create_party_confirm.html', {'current_lobby': current_lobby})

    if current_lobby:
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
        
        if current_lobby and current_lobby != lobby:
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