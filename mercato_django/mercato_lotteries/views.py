from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from mercato_accounts.models import Profile
from mercato_payments.models import PaymentTransaction

from .models import Categoria, Auction, Bid, Regione, AuctionResult
from .tasks import close_auction


def lottery_list(request):
    """List all active auctions"""
    auctions_qs = (
        Auction.objects.filter(status='active')
        .select_related('regione', 'categoria')
        .annotate(bids_count=Count('bids'))
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
        request, 'lotteries/list.html',
        {'page_obj': page_obj, 'auctions': page_obj.object_list, 'query': query,
         'regioni': regioni, 'categorie': categorie,
         'selected_regione_id': int(regione_id) if regione_id else None,
         'selected_categoria_id': int(categoria_id) if categoria_id else None,
         'querystring': querystring},
    )


def lottery_detail(request, lottery_id):
    """Auction detail view with bid history"""
    auction = get_object_or_404(
        Auction.objects.select_related('regione', 'categoria').annotate(
            bids_count=Count('bids')
        ),
        id=lottery_id, status='active',
    )

    user_bids = []
    if request.user.is_authenticated:
        user_bids = Bid.objects.filter(auction=auction, bidder=request.user).order_by('-placed_at').all()

    # Recent bids (last 10, anonymized)
    recent_bids = (
        Bid.objects.filter(auction=auction, status='completed')
        .select_related('bidder')
        .order_by('-placed_at')[:10]
    )
    
    recent_bid_history = []
    for bid in recent_bids:
        anonymized_bidder = f"User_{bid.bidder.id:04d}"
        recent_bid_history.append({
            'amount': bid.amount,
            'bidder_anonymized': anonymized_bidder,
            'placed_at': bid.placed_at
        })

    seller_profile = None
    try:
        seller_profile = auction.seller.profile
    except Profile.DoesNotExist:
        seller_profile = None

    seller_rating = 4.8
    seller_total_sales = Auction.objects.filter(seller=auction.seller, status='completed').count()

    current_time = timezone.now()

    return render(
        request, 'lotteries/detail.html',
        {'lottery': auction, 'user_bids': user_bids, 'recent_bid_history': recent_bid_history,
         'seller_profile': seller_profile, 'seller_rating': seller_rating,
         'seller_total_sales': seller_total_sales, 'now': current_time},
    )


@login_required
def place_bid(request, lottery_id):
    """Place a bid on an auction"""
    auction = get_object_or_404(Auction, id=lottery_id, status='active')

    if auction.is_expired:
        messages.error(request, "Spiacente, questa asta è scaduta.")
        return redirect('lotteries:detail', lottery_id=lottery_id)
    
    if request.user == auction.seller:
        messages.error(request, "Non puoi fare offerte sulla tua stessa asta.")
        return redirect('lotteries:detail', lottery_id=lottery_id)
    
    if request.method == 'POST':
        try:
            bid_amount = Decimal(request.POST.get('bid_amount'))
            min_bid = auction.minimum_next_bid
            
            if bid_amount < min_bid:
                messages.error(request, f"L'offerta minima è €{min_bid}. Incremento: €{auction.bid_increment}")
                return render(request, 'lotteries/place_bid.html', {'auction': auction, 'min_bid': min_bid})
            
            # Create bid
            bid = Bid.objects.create(
                auction=auction, bidder=request.user, amount=bid_amount, status='pending'
            )
            
            # Create payment transaction
            payment_transaction = PaymentTransaction.objects.create(
                ticket_id=bid.id,
                amount=bid_amount, status='pending'
            )
            
            return redirect('payments:process_payment', ticket_id=str(bid.id))
            
        except (ValueError, ValidationError) as e:
            messages.error(request, f"Errore durante l'inserimento dell'offerta: {str(e)}")
    
    min_bid = auction.minimum_next_bid
    return render(request, 'lotteries/place_bid.html', {'auction': auction, 'min_bid': min_bid})


@login_required
def my_bids(request):
    """Show all bids placed by the current user"""
    bids = Bid.objects.filter(bidder=request.user).select_related('auction').order_by('-placed_at')
    return render(request, 'lotteries/my_bids.html', {'bids': bids})


def lottery_results(request):
    """Show auction results"""
    return render(request, 'lotteries/results.html')


@login_required
def close_auction_view(request, lottery_id):
    """Close an auction manually (seller only)"""
    auction = get_object_or_404(Auction, id=lottery_id)

    if request.user != auction.seller:
        messages.error(request, "Non hai accesso a questa asta")
        return redirect('lotteries:detail', lottery_id=lottery_id)

    if auction.status != 'active':
        messages.error(request, "Questa asta non è attiva")
        return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)

    if not auction.bids.exists():
        messages.error(request, "Non ci sono offerte su questa asta")
        return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)

    close_auction.delay(lottery_id)
    messages.success(request, "Chiusura asta avviata! Il vincitore verrà determinato a breve.")
    return redirect('accounts:seller_lottery_detail', lottery_id=lottery_id)


# Backwards compatibility aliases
buy_tickets = place_bid
my_tickets = my_bids
initiate_draw = close_auction_view
