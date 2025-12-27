from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Lottery, LotteryTicket
from mercato_payments.models import PaymentTransaction, PaymentSettings
from mercato_accounts.models import Profile


def lottery_list(request):
    lotteries_qs = (
        Lottery.objects.filter(status='active')
        .annotate(
            tickets_sold_count=Count(
                'tickets', filter=Q(tickets__payment_status='completed')
            )
        )
        .order_by('-created_at')
    )

    query = (request.GET.get('q') or '').strip()
    if query:
        lotteries_qs = lotteries_qs.filter(title__icontains=query)

    paginator = Paginator(lotteries_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'lotteries/list.html',
        {
            'page_obj': page_obj,
            'lotteries': page_obj.object_list,
            'query': query,
            'categories': [],
            'selected_category': None,
        },
    )


def lottery_detail(request, lottery_id):
    lottery = get_object_or_404(
        Lottery.objects.annotate(
            tickets_sold_count=Count(
                'tickets', filter=Q(tickets__payment_status='completed')
            )
        ),
        id=lottery_id,
        status='active',
    )

    user_tickets = []
    if request.user.is_authenticated:
        user_tickets = (
            LotteryTicket.objects.filter(lottery=lottery, buyer=request.user)
            .order_by('-purchased_at')
            .all()
        )

    # Recent purchases (last 10 tickets sold, anonymized)
    recent_tickets = (
        LotteryTicket.objects.filter(lottery=lottery, payment_status='completed')
        .select_related('buyer')
        .order_by('-purchased_at')[:10]
    )
    
    # Prepare anonymized recent purchases
    recent_purchases = []
    for ticket in recent_tickets:
        anonymized_buyer = f"User_{ticket.buyer.id:04d}"  # Anonymize buyer identity
        recent_purchases.append({
            'ticket_number': ticket.ticket_number,
            'buyer_anonymized': anonymized_buyer,
            'purchased_at': ticket.purchased_at
        })

    # Check if seller has profile for additional data
    seller_profile = None
    try:
        seller_profile = lottery.seller.profile
    except Profile.DoesNotExist:
        seller_profile = None

    # Calculate seller rating (placeholder - can be enhanced later)
    seller_rating = 4.8  # Placeholder rating
    seller_total_sales = Lottery.objects.filter(seller=lottery.seller, status='completed').count()

    # Check for low ticket notifications (last 5 tickets)
    low_ticket_warning = lottery.tickets_remaining <= 5 and lottery.tickets_remaining > 0
    current_time = timezone.now()

    return render(
        request,
        'lotteries/detail.html',
        {
            'lottery': lottery,
            'user_tickets': user_tickets,
            'recent_purchases': recent_purchases,
            'seller_profile': seller_profile,
            'seller_rating': seller_rating,
            'seller_total_sales': seller_total_sales,
            'low_ticket_warning': low_ticket_warning,
            'now': current_time,
        },
    )


@login_required
def buy_tickets(request, lottery_id):
    lottery = get_object_or_404(Lottery, id=lottery_id, status='active')

    # Check if lottery is still available for purchase
    if lottery.tickets_remaining <= 0:
        messages.error(request, "Spiacente, questa lotteria è esaurita.")
        return redirect('mercato_lotteries:detail', lottery_id=lottery_id)

    # Check expiration date
    if lottery.expiration_date and lottery.expiration_date <= timezone.now():
        messages.error(request, "Spiacente, questa lotteria è scaduta.")
        return redirect('mercato_lotteries:detail', lottery_id=lottery_id)
    
    if request.method == 'POST':
        try:
            ticket_count = int(request.POST.get('ticket_count', 1))
            if ticket_count < 1 or ticket_count > lottery.tickets_remaining:
                messages.error(request, f"Numero di biglietti non valido. Massimo disponibile: {lottery.tickets_remaining}")
                return render(request, 'lotteries/buy_tickets.html', {'lottery': lottery})
            
            # Calculate total amount
            total_amount = lottery.ticket_price * ticket_count
            
            # Create tickets (initially pending)
            created_tickets = []
            for i in range(ticket_count):
                ticket = LotteryTicket.objects.create(
                    lottery=lottery,
                    buyer=request.user,
                    payment_status='pending'
                )
                created_tickets.append(ticket)
            
            # Create payment transaction
            payment_transaction = PaymentTransaction.objects.create(
                ticket=created_tickets[0],  # Use first ticket for transaction reference
                amount=total_amount,
                status='pending'
            )
            
            # Store ticket IDs in the transaction for reference
            payment_transaction.ticket_ids = [ticket.id for ticket in created_tickets]
            payment_transaction.save()
            
            # Redirect to PayPal payment processing with ticket count
            return redirect('payments:process_payment', ticket_id=created_tickets[0].id)
            
        except (ValueError, ValidationError) as e:
            messages.error(request, f"Errore durante l'elaborazione dell'acquisto: {str(e)}")
    
    return render(request, 'lotteries/buy_tickets.html', {'lottery': lottery})


@login_required
def my_tickets(request):
    tickets = (
        LotteryTicket.objects.filter(buyer=request.user)
        .select_related('lottery')
        .order_by('-purchased_at')
    )
    return render(request, 'lotteries/my_tickets.html', {'tickets': tickets})


def lottery_results(request):
    return render(request, 'lotteries/results.html')
