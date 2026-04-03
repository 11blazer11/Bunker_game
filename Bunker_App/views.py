from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from charachteristics import *
from django.contrib import messages
from .utils import login_required_message
import random

#register, login, logout
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()  
            return redirect('login')
        
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)
            return redirect('main') 
        else:
            messages.error(request, "Invalid username or password")

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