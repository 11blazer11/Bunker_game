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
