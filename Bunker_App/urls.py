from django.urls import path
from .views import register_view, login_view, logout_view, main_view, create_party_view, find_party_view, join_party_view, activate

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', main_view, name='main'),
    path('create/', create_party_view, name='create_party'),
    path('find/', find_party_view, name='find_party'),
    path('join/', join_party_view, name='join_party'),

    path('activate/<token>/', activate, name='activate'),
]