from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.signing import dumps, loads, BadSignature, SignatureExpired
from .forms import CustomUserCreationForm
from .models import Lobby
from .charachteristics import *
from django.contrib import messages
from .utils import login_required_message
import random

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
    message = render_to_string('verify_email.html', {
        'user': username,
        'domain': get_current_site(request).domain,
        'token': token,
        'protocol': 'https' if request.is_secure() else 'http',
    })

    email = EmailMessage(mail_subject, message, to=[email_address])
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
    return render(request, 'main_page.html', {'user_lobbies': user_lobbies})


@login_required_message
def join_party_view(request):
    if request.method == 'POST':
        code = request.POST.get('party_code')
        try:
            lobby = Lobby.objects.get(code=code)
            if request.user in lobby.participants.all():
                messages.warning(request, 'You are already in this lobby.')
                return redirect('lobby_detail', lobby_id=lobby.id)
            if lobby.participants.count() >= MAX_LOBBY_PARTICIPANTS:
                messages.error(request, f'Lobby is full. Maximum {MAX_LOBBY_PARTICIPANTS} participants allowed.')
                return redirect('join_party')
            # Remove user from any existing lobbies
            request.user.joined_lobbies.clear()
            lobby.participants.add(request.user)
            messages.success(request, f'Joined lobby "{lobby.name}"')
            return redirect('lobby_detail', lobby_id=lobby.id)
        except Lobby.DoesNotExist:
            messages.error(request, 'Lobby with this code does not exist.')
    return render(request, 'join_party.html')

 
@login_required_message
def create_party_view(request):
    # Automatically create a lobby when the user loads this page.
    # The lobby name is generated from the creator username.
    request.user.joined_lobbies.clear()
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
    lobbies = Lobby.objects.filter(name__icontains=query) if query else Lobby.objects.none()
    return render(request, 'find_party.html', {'lobbies': lobbies})


@login_required_message
def lobby_detail_view(request, lobby_id):
    try:
        lobby = Lobby.objects.get(id=lobby_id)
        if request.user not in lobby.participants.all():
            messages.error(request, 'You are not a participant in this lobby.')
            return redirect('main')
        
        if request.method == 'POST' and request.user == lobby.creator:
            action = request.POST.get('action')
            if action == 'kick':
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
            elif action == 'delete':
                lobby.delete()
                messages.success(request, 'Lobby deleted successfully.')
                return redirect('main')
        
        return render(request, 'lobby_detail.html', {'lobby': lobby})
    except Lobby.DoesNotExist:
        messages.error(request, 'Lobby does not exist.')
        return redirect('main')