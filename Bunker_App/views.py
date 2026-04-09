from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm
from .charachteristics import *
from django.contrib import messages
from .utils import login_required_message
import random
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail, EmailMessage
from .tokens import account_activation_token
from django.contrib.auth import get_user_model
from django.urls import reverse

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Thank you for your email confirmation. You can now login to your account.')
        return redirect('login')  
    else:
        messages.error(request, 'Activation link is invalid!')
        return redirect('login')

def verify_email(request,  user, to_email):
    mail_subject = 'Activate your user acount'
    message = render_to_string('verify_email.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http',
    })

    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f'Please confirm your email address to complete the registration. We have sent you an email to {to_email}')
    else:
        messages.error(request, f'Problem sending email to {to_email}, check if you typed it correctly.')


def register_view(request):
    form = CustomUserCreationForm(request.POST)
    if request.method == "POST":
        
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # ❗ disable account until email verified
            user.save()
            verify_email(request, user, form.cleaned_data.get('email'))
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
                    return redirect('main')  # main page
                else:
                    messages.error(request, "Invalid password!")
                    return redirect('login')
            else:
                # User exists but email not verified → redirect to verify page
                return redirect('verify_email')
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