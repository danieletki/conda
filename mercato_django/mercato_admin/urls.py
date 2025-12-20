from django.urls import path
from . import views

app_name = 'admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.user_management, name='users'),
    path('lotteries/', views.lottery_management, name='lotteries'),
    path('payments/', views.payment_management, name='payments'),
    path('settings/', views.site_settings, name='settings'),
    path('reports/', views.reports, name='reports'),
    path('logs/', views.system_logs, name='logs'),
]