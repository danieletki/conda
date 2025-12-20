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
    # Seller Dashboard URLs
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/lottery/create/', views.seller_create_lottery, name='seller_create_lottery'),
    path('seller/lottery/<int:lottery_id>/', views.seller_lottery_detail, name='seller_lottery_detail'),
    path('seller/reports/', views.seller_reports, name='seller_reports'),
    path('seller/kyc/settings/', views.seller_kyc_settings, name='seller_kyc_settings'),
]