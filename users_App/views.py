from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.signing import dumps, loads, BadSignature, SignatureExpired
from .forms import CustomUserCreationForm
from .models import Friend, Profile
from django.contrib import messages
from .utils import login_required_message
from django.db.models import Q

from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives

ACTIVATION_SALT = 'activate-account'
ACTIVATION_MAX_AGE = 60 * 60 * 24


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
def account_view(request):
    return render(request, 'account.html')


@login_required_message
def friends_view(request):
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
