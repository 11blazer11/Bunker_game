from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm
from .charachteristics import *
from django.contrib import messages
from .utils import login_required_message
import random

#register, login, logout
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse

def register_view(request):
    form = CustomUserCreationForm(request.POST)
    if request.method == "POST":
        
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # ❗ disable account until email verified
            user.save()

            # Generate token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            domain = get_current_site(request).domain
            link = f"http://{domain}{reverse('verify_email', args=[uid, token])}"

            # Send email
            send_mail(
                'Verify your account',
                f'Click this link to verify your account:\n{link}',
                'your_email@gmail.com',
                [user.email],
                fail_silently=False,
            )

            return redirect('login')

    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.models import User

def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Email verified! You can now login.")
        return redirect('login')
    else:
        messages.error(request, "Invalid or expired link.")
        return redirect('login')


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            if user.is_active:
                login(request, user)
                return redirect('main')
        else:
            messages.error(request, "Verify your email first!")

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