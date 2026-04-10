from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.signing import dumps, loads, BadSignature, SignatureExpired
from .forms import CustomUserCreationForm
from .charachteristics import *
from django.contrib import messages
from .utils import login_required_message
import random
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
    return render(request, 'main_page.html')


@login_required_message
def join_party_view(request):
    return render(request, 'join_party.html')


@login_required_message
def create_party_view(request):
    return render(request, 'create_party.html')


@login_required_message
def find_party_view(request):
    return render(request, 'find_party.html')