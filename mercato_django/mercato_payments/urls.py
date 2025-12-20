from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('process/<uuid:ticket_id>/', views.process_payment, name='process_payment'),
    path('history/', views.payment_history, name='history'),
    path('transaction/<uuid:transaction_id>/', views.payment_detail, name='payment_detail'),
    path('paypal/create-order/', views.paypal_create_order, name='paypal_create_order'),
    path('paypal/capture-order/', views.paypal_capture_order, name='paypal_capture_order'),
    path('paypal/success/<uuid:ticket_id>/', views.paypal_success, name='paypal_success'),
    path('paypal/cancel/<uuid:ticket_id>/', views.paypal_cancel, name='paypal_cancel'),
    path('paypal/ipn/', views.paypal_ipn_webhook, name='paypal_ipn_webhook'),
    path('refund/<uuid:ticket_id>/', views.refund_ticket_view, name='refund_ticket'),
    path('process/', views.process_payment, name='process'),
]