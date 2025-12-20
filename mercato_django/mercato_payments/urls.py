from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('process/', views.process_payment, name='process'),
    path('history/', views.payment_history, name='history'),
    path('<uuid:payment_id>/', views.payment_detail, name='detail'),
    path('paypal/create-order/', views.paypal_create_order, name='paypal_create_order'),
    path('paypal/capture-order/', views.paypal_capture_order, name='paypal_capture_order'),
]