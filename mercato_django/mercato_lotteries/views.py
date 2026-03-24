from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from decimal import Decimal

from mercato_accounts.models import Profile
from mercato_payments.models import PaymentTransaction

from .models import (
    Categoria, Lottery, LotteryTicket, Regione, WinnerDrawing,
    Auction, Bid, AuctionResult
)
from .tasks import perform_manual_draw


def lottery_list(request):
    lotteries_qs = (
        Lottery.objects.filter(status='active')
        .select_related('regione', 'categoria')
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

    regione_id = request.GET.get('regione_id')
    if regione_id and str(regione_id).isdigit():
        lotteries_qs = lotteries_qs.filter(regione_id=int(regione_id))
    else:
        regione_id = None

    categoria_id = request.GET.get('categoria_id')
    if categoria_id and str(categoria_id).isdigit():
        lotteries_qs = lotteries_qs.filter(categoria_id=int(categoria_id))
    else:
        categoria_id = None

    regioni = Regione.objects.order_by('id')
    categorie = Categoria.objects.order_by('name')

    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    paginator = Paginator(lotteries_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'lotteries/list.html',
        {
            'page_obj': page_obj,
            'lotteries': page_obj.object_list,
            'query': query,
            'regioni': regioni,
            'categorie': categorie,
            'selected_regione_id': int(regione_id) if regione_id else None,
            'selected_categoria_id': int(categoria_id) if categoria_id else None,
            'querystring': querystring,
        },
    )


def lottery_detail(request, lottery_id):
    lottery = get_object_or_404(
        Lottery.objects.select_related('regione', 'categoria').annotate(
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
    low_ticket_warning = (
        not lottery.can_manually_draw
        and lottery.tickets_remaining <= 5
        and lottery.tickets_remaining > 0
    )
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

    # Check expiration date
    if lottery.expiration_date and lottery.expiration_date <= timezone.now():
        messages.error(request, "Spiacente, questa lotteria è scaduta.")
        return redirect('lotteries:detail', lottery_id=lottery_id)
    
    if request.method == 'POST':
        try:
            ticket_count = int(request.POST.get('ticket_count', 1))
            if ticket_count < 1:
                messages.error(request, "Numero di biglietti non valido. Minimo: 1")
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
            
            # Store ticket IDs in the transaction for reference (converted to strings for JSON serialization)
            payment_transaction.ticket_ids = [str(ticket.id) for ticket in created_tickets]
            payment_transaction.save()
            
            # Redirect to PayPal payment processing with ticket count
            return redirect('payments:process_payment', ticket_id=str(created_tickets[0].id))
            
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


@login_required
def initiate_draw(request, lottery_id):
    """
    Inizia il processo di estrazione manuale del vincitore.
    Disponibile solo per il venditore della lotteria.
    """
    lottery = get_object_or_404(Lottery, id=lottery_id)

    # 1. Lotteria esiste e status='active'
    if lottery.status != 'active':
        messages.error(request, "Questa lotteria non è attiva")
        return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)

    # 2. L'utente è il venditore (request.user == lottery.seller)
    if request.user != lottery.seller:
        messages.error(request, "Non hai accesso a questa lotteria")
        # If it's not the seller, maybe they shouldn't even know this exists or be redirected to buyer detail
        return redirect('lotteries:detail', lottery_id=lottery_id)

    # 3. Sono passate almeno min_draw_delay_hours ore dalla creazione
    time_elapsed = timezone.now() - lottery.created_at
    if time_elapsed < timedelta(hours=lottery.min_draw_delay_hours):
        remaining = timedelta(hours=lottery.min_draw_delay_hours) - time_elapsed
        hours = int(remaining.total_seconds() // 3600)
        messages.error(request, f"Devi attendere {hours} ore prima di poter estrarre")
        return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)

    # 4. Esiste almeno 1 biglietto con payment_status='completed'
    if not lottery.tickets.filter(payment_status='completed').exists():
        messages.error(request, "Nessun biglietto pagato disponibile")
        return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)

    # 5. Non esiste già un WinnerDrawing per questa lotteria
    if WinnerDrawing.objects.filter(lottery=lottery).exists():
        messages.error(request, "L'estrazione è già stata effettuata")
        return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)

    # Se tutte validazioni passano:
    perform_manual_draw.delay(lottery_id, request.user.id)
    messages.success(request, "Estrazione avviata! Il vincitore verrà estratto a breve.")
    return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)


# =====================================================================
# AUCTION VIEWS
# =====================================================================

def auction_list(request):
    """
    Display list of active auctions
    """
    auctions_qs = (
        Auction.objects.filter(status='active')
        .select_related('regione', 'categoria', 'seller', 'current_highest_bidder')
        .annotate(
            bids_count_annotation=Count(
                'bids', filter=Q(bids__status='active')
            )
        )
        .order_by('-created_at')
    )

    query = (request.GET.get('q') or '').strip()
    if query:
        auctions_qs = auctions_qs.filter(title__icontains=query)

    regione_id = request.GET.get('regione_id')
    if regione_id and str(regione_id).isdigit():
        auctions_qs = auctions_qs.filter(regione_id=int(regione_id))
    else:
        regione_id = None

    categoria_id = request.GET.get('categoria_id')
    if categoria_id and str(categoria_id).isdigit():
        auctions_qs = auctions_qs.filter(categoria_id=int(categoria_id))
    else:
        categoria_id = None

    regioni = Regione.objects.order_by('id')
    categorie = Categoria.objects.order_by('name')

    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()

    paginator = Paginator(auctions_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'lotteries/auction_list.html',
        {
            'page_obj': page_obj,
            'auctions': page_obj.object_list,
            'query': query,
            'regioni': regioni,
            'categorie': categorie,
            'selected_regione_id': int(regione_id) if regione_id else None,
            'selected_categoria_id': int(categoria_id) if categoria_id else None,
            'querystring': querystring,
        },
    )


def auction_detail(request, auction_id):
    """
    Display details for a specific auction
    """
    auction = get_object_or_404(
        Auction.objects.select_related('regione', 'categoria', 'seller', 'current_highest_bidder').annotate(
            bids_count_annotation=Count(
                'bids', filter=Q(bids__status='active')
            )
        ),
        id=auction_id,
    )

    user_bids = []
    if request.user.is_authenticated:
        user_bids = (
            Bid.objects.filter(auction=auction, bidder=request.user)
            .order_by('-created_at')
            .all()
        )

    # Recent bids (last 10 bids, anonymized for non-seller users)
    recent_bids_qs = Bid.objects.filter(auction=auction, status='active').order_by('-created_at')[:10]
    recent_bids = []
    for bid in recent_bids_qs:
        is_seller_or_owner = (
            request.user == auction.seller or 
            request.user == bid.bidder
        )
        anonymized_bidder = f"User_{bid.bidder.id:04d}" if not is_seller_or_owner else bid.bidder.username
        recent_bids.append({
            'amount': bid.amount,
            'bidder_anonymized': anonymized_bidder,
            'created_at': bid.created_at
        })

    # Seller profile
    seller_profile = None
    try:
        seller_profile = auction.seller.profile
    except Profile.DoesNotExist:
        seller_profile = None

    # Calculate seller rating (placeholder - can be enhanced later)
    seller_rating = 4.8  # Placeholder rating
    seller_total_sales = Auction.objects.filter(seller=auction.seller, status='completed').count()

    # Check if auction is ending soon (last 5 bids or time)
    ending_soon_warning = (
        auction.status == 'active' and
        auction.auction_end_time and
        (auction.auction_end_time - timezone.now()) < timedelta(hours=1)
    )

    current_time = timezone.now()

    return render(
        request,
        'lotteries/auction_detail.html',
        {
            'auction': auction,
            'user_bids': user_bids,
            'recent_bids': recent_bids,
            'seller_profile': seller_profile,
            'seller_rating': seller_rating,
            'seller_total_sales': seller_total_sales,
            'ending_soon_warning': ending_soon_warning,
            'now': current_time,
        },
    )


@login_required
def place_bid(request, auction_id):
    """
    Place a bid on an auction
    """
    auction = get_object_or_404(Auction, id=auction_id)

    if auction.status != 'active':
        messages.error(request, "L'asta non è attiva")
        return redirect('lotteries:auction_detail', auction_id=auction_id)

    if auction.is_expired:
        messages.error(request, "L'asta è scaduta")
        return redirect('lotteries:auction_detail', auction_id=auction_id)

    if request.method == 'POST':
        try:
            bid_amount = Decimal(str(request.POST.get('bid_amount', '0')))
            if bid_amount <= 0:
                messages.error(request, "L'importo dell'offerta non è valido")
                return redirect('lotteries:auction_detail', auction_id=auction_id)

            # Place the bid
            bid = auction.place_bid(request.user, bid_amount)

            # Create payment transaction for bid deposit
            payment_transaction = PaymentTransaction.objects.create(
                ticket=None,  # No ticket for auctions
                amount=bid_amount,
                status='pending'
            )
            payment_transaction.save()

            # Redirect to PayPal payment processing
            messages.success(request, f"Offerta di {bid_amount:.2f} EUR piazzata con successo!")
            return redirect('payments:process_payment', ticket_id=str(bid.id))

        except (ValueError, ValidationError) as e:
            messages.error(request, f"Errore durante l'elaborazione dell'offerta: {str(e)}")

    return redirect('lotteries:auction_detail', auction_id=auction_id)


@login_required
def my_bids(request):
    """
    Display user's bids
    """
    bids = (
        Bid.objects.filter(bidder=request.user)
        .select_related('auction')
        .order_by('-created_at')
    )
    return render(request, 'lotteries/my_bids.html', {'bids': bids})


@login_required
def close_auction(request, auction_id):
    """
    Close an auction manually (seller only)
    """
    auction = get_object_or_404(Auction, id=auction_id)

    if request.user != auction.seller:
        messages.error(request, "Non hai accesso a questa asta")
        return redirect('lotteries:auction_detail', auction_id=auction_id)

    try:
        result = auction.close_auction()
        messages.success(
            request,
            f"Asta chiusa! " +
            (f"Vincitore: {result.winner.username} - {result.final_price:.2f} EUR" if result.winner else "Nessun vincitore")
        )
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect('lotteries:auction_detail', auction_id=auction_id)


@login_required
def cancel_auction(request, auction_id):
    """
    Cancel an auction (seller only)
    """
    auction = get_object_or_404(Auction, id=auction_id)

    if request.user != auction.seller:
        messages.error(request, "Non hai accesso a questa asta")
        return redirect('lotteries:auction_detail', auction_id=auction_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        try:
            auction.cancel_auction(reason)
            messages.success(request, "Asta annullata con successo")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('lotteries:auction_detail', auction_id=auction_id)

    return render(request, 'lotteries/cancel_auction.html', {'auction': auction})
