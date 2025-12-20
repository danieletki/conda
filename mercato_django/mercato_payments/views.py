from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@login_required
def dashboard(request):
    """
    Payment dashboard
    """
    return render(request, 'payments/dashboard.html')


@login_required
def process_payment(request):
    """
    Process a payment
    """
    # This will be implemented with PayPal integration
    return render(request, 'payments/process.html')


@login_required
def payment_history(request):
    """
    Display payment history
    """
    return render(request, 'payments/history.html')


@login_required
def payment_detail(request, payment_id):
    """
    Display payment details
    """
    return render(request, 'payments/detail.html')


@login_required
def paypal_create_order(request):
    """
    Create PayPal order
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        # PayPal integration will be implemented here
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def paypal_capture_order(request):
    """
    Capture PayPal order
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        # PayPal integration will be implemented here
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Invalid request'}, status=400)