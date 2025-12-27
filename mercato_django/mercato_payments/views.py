from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
import json
import logging
from .models import PaymentTransaction, PaymentSettings
from mercato_lotteries.models import LotteryTicket
from .paypal import PayPalClient, process_paypal_ipn, refund_ticket_payment

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """
    Payment dashboard with transaction reports
    """
    # Get transaction statistics
    user_transactions = PaymentTransaction.objects.filter(ticket__buyer=request.user)
    
    # Overview statistics
    total_paid = user_transactions.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_commission = user_transactions.filter(status='completed').aggregate(
        total=Sum('commission')
    )['total'] or 0
    
    recent_transactions = user_transactions.select_related(
        'ticket', 'ticket__lottery'
    ).order_by('-created_at')[:10]
    
    # For admin/staff, show all transactions
    if request.user.is_staff or request.user.is_superuser:
        all_transactions = PaymentTransaction.objects.all()
        total_revenue = all_transactions.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_platform_commission = all_transactions.filter(status='completed').aggregate(
            total=Sum('commission')
        )['total'] or 0
        
        context = {
            'total_revenue': total_revenue,
            'total_paid': total_revenue,  # total_paid = total_revenue (importo lordo pagato dai buyer)
            'total_platform_commission': total_platform_commission,
            'total_commission': total_platform_commission,  # Same as total_platform_commission for admin view
            'transaction_count': all_transactions.count(),
            'recent_transactions': all_transactions.select_related(
                'ticket', 'ticket__lottery', 'ticket__buyer'
            ).order_by('-created_at')[:20],
            'is_admin_view': True
        }
    else:
        context = {
            'total_paid': total_paid,
            'total_revenue': total_paid,  # Same as total_paid for non-admin view
            'total_platform_commission': total_commission,
            'total_commission': total_commission,  # Commission paid by this user
            'transaction_count': user_transactions.count(),
            'recent_transactions': recent_transactions,
            'is_admin_view': False
        }
    
    return render(request, 'payments/dashboard.html', context)


@login_required
def payment_history(request):
    """
    Display complete payment history for the user
    """
    transactions = PaymentTransaction.objects.filter(
        ticket__buyer=request.user
    ).select_related('ticket', 'ticket__lottery').order_by('-created_at')
    
    return render(request, 'payments/history.html', {
        'transactions': transactions
    })


@login_required
def payment_detail(request, transaction_id):
    """
    Display payment transaction details
    """
    transaction = get_object_or_404(
        PaymentTransaction.objects.select_related(
            'ticket', 'ticket__lottery', 'ticket__buyer'
        ),
        id=transaction_id
    )
    
    # Ensure user can only view their own transactions unless admin
    if not request.user.is_staff and transaction.ticket.buyer != request.user:
        messages.error(request, "Access denied.")
        return redirect('payments:dashboard')
    
    return render(request, 'payments/detail.html', {
        'transaction': transaction
    })


@login_required
def process_payment(request, ticket_id):
    """
    Initiate payment process for a specific ticket
    """
    ticket = get_object_or_404(LotteryTicket, id=ticket_id)
    
    # Ensure user owns the ticket
    if ticket.buyer != request.user:
        messages.error(request, "Access denied.")
        return redirect('mercato_lotteries:list')
    
    # Check if ticket is already paid
    if ticket.payment_status == 'completed':
        messages.warning(request, "This ticket has already been paid.")
        return redirect('payments:dashboard')
    
    # Get ticket price
    amount = ticket.lottery.ticket_price
    
    # Calculate commission
    commission = (Decimal(amount) * Decimal('0.10')).quantize(Decimal('0.01'))
    net_amount = Decimal(amount) - commission
    
    context = {
        'ticket': ticket,
        'amount': amount,
        'commission': commission,
        'net_amount': net_amount,
    }
    
    return render(request, 'payments/process.html', context)


@login_required
def paypal_create_order(request):
    """
    Create PayPal order for a lottery ticket
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_id = data.get('ticket_id')
            
            # Get ticket and validate ownership
            ticket = get_object_or_404(LotteryTicket, id=ticket_id)
            if ticket.buyer != request.user:
                return JsonResponse({'error': 'Access denied'}, status=403)
            
            # Get amount
            amount = ticket.lottery.ticket_price
            
            # Initialize PayPal client
            paypal_client = PayPalClient()
            
            # Generate return and cancel URLs
            return_url = request.build_absolute_uri(
                reverse('payments:paypal_success', args=[ticket_id])
            )
            cancel_url = request.build_absolute_uri(
                reverse('payments:paypal_cancel', args=[ticket_id])
            )
            
            # Create PayPal order
            order_response = paypal_client.create_order(
                ticket, amount, return_url, cancel_url
            )
            
            # Store PayPal order ID in transaction
            transaction, created = PaymentTransaction.objects.get_or_create(
                ticket=ticket,
                defaults={
                    'amount': amount,
                    'status': 'pending',
                }
            )
            transaction.paypal_order_id = order_response['id']
            transaction.save()
            
            return JsonResponse({
                'status': 'success',
                'order_id': order_response['id'],
                'approve_url': next(
                    (link['href'] for link in order_response.get('links', [])
                     if link['rel'] == 'approve'), None
                )
            })
            
        except Exception as e:
            logger.error(f"Error creating PayPal order: {str(e)}")
            return JsonResponse({'error': 'Failed to create order'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def paypal_capture_order(request):
    """
    Capture PayPal order and process payment
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            ticket_id = data.get('ticket_id')
            
            # Get ticket
            ticket = get_object_or_404(LotteryTicket, id=ticket_id)
            
            # Initialize PayPal client
            paypal_client = PayPalClient()
            
            # Capture the order
            capture_response = paypal_client.capture_order(order_id)
            
            if capture_response['status'] == 'COMPLETED':
                # Get transaction details
                purchase_units = capture_response.get('purchase_units', [{}])[0]
                payments = purchase_units.get('payments', {})
                captures = payments.get('captures', [{}])
                capture = captures[0] if captures else {}
                
                payer_info = capture_response.get('payer', {})
                
                # Update transaction
                transaction = PaymentTransaction.objects.filter(
                    paypal_order_id=order_id
                ).first()
                
                if transaction:
                    transaction.paypal_tx_id = capture.get('id')
                    transaction.payer_email = payer_info.get('email_address')
                    transaction.paypal_fee_amount = Decimal(
                        capture.get('seller_receivable_breakdown', {})
                        .get('paypal_fee', {}).get('value', '0')
                    )
                    transaction.mark_as_completed()
                
                return JsonResponse({
                    'status': 'success',
                    'transaction_id': str(transaction.id) if transaction else None
                })
            else:
                # Update transaction status to failed
                transaction = PaymentTransaction.objects.filter(
                    paypal_order_id=order_id
                ).first()
                if transaction:
                    transaction.status = 'failed'
                    transaction.save()
                
                return JsonResponse({
                    'status': 'failed',
                    'message': 'Payment capture failed'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error capturing PayPal order: {str(e)}")
            return JsonResponse({'error': 'Failed to capture order'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def paypal_success(request, ticket_id):
    """
    Handle successful PayPal payment
    """
    messages.success(request, "Payment completed successfully!")
    return redirect('payments:payment_detail', transaction_id=request.GET.get('transaction_id'))


@login_required
def paypal_cancel(request, ticket_id):
    """
    Handle cancelled PayPal payment
    """
    ticket = get_object_or_404(LotteryTicket, id=ticket_id)
    
    # Update transaction status to cancelled
    transaction = PaymentTransaction.objects.filter(
        ticket=ticket,
        status='pending'
    ).first()
    
    if transaction:
        transaction.status = 'cancelled'
        transaction.save()
    
    messages.warning(request, "Payment was cancelled. You can try again.")
    return redirect('payments:process_payment', ticket_id=ticket_id)


@csrf_exempt
def paypal_ipn_webhook(request):
    """
    Receive and process PayPal IPN webhook notifications
    """
    if request.method == 'POST':
        try:
            # Parse webhook data
            webhook_data = json.loads(request.body)
            
            # Process the IPN
            success = process_paypal_ipn(webhook_data)
            
            if success:
                return HttpResponse(status=200)
            else:
                return HttpResponse(status=400)
                
        except Exception as e:
            logger.error(f"Error processing PayPal webhook: {str(e)}")
            return HttpResponse(status=500)
    
    return HttpResponse(status=400)


@login_required
def refund_ticket_view(request, ticket_id):
    """
    Process refund for a specific ticket (for admin use)
    """
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('payments:dashboard')
    
    ticket = get_object_or_404(LotteryTicket, id=ticket_id)
    
    success = refund_ticket_payment(ticket)
    
    if success:
        messages.success(request, f"Refund processed successfully for ticket {ticket.ticket_number}")
    else:
        messages.error(request, f"Failed to process refund for ticket {ticket.ticket_number}")
    
    return redirect('payments:dashboard')