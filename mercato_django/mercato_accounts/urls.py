from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('contact/', views.contact, name='contact'),
    path('privacy/', views.privacy, name='privacy'),
    path('buyer/dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('buyer/profile/edit/', views.buyer_profile_edit, name='buyer_profile_edit'),
    path('buyer/change-password/', views.buyer_change_password, name='buyer_change_password'),
]