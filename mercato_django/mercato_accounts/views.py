from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from mercato_lotteries.models import Auction, Bid, AuctionResult
from mercato_payments.models import Payment, PaymentTransaction
from mercato_lotteries.forms import AuctionCreationForm
from mercato_lotteries.tasks import close_auction

from .forms import CustomUserCreationForm, CustomUserLoginForm, ProfileForm, UserSettingsForm, CustomPasswordChangeForm
from .models import CustomUser, Profile


def home(request):
    auctions_qs = Auction.objects.filter(status='active').annotate(
        bids_count=Count('bids')
    )
    featured_auctions = auctions_qs.order_by('-bids_count', '-created_at')[:3]
    latest_auctions = auctions_qs.order_by('-created_at')[:6]
    return render(request, 'home.html', {'featured_lotteries': featured_auctions, 'latest_lotteries': latest_auctions})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('lotteries:list')
    if request.method == 'POST':
        form = CustomUserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Benvenuto {user.username}!')
            return redirect('lotteries:list')
        else:
            messages.error(request, 'Credenziali non valide.')
    else:
        form = CustomUserLoginForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        messages.success(request, 'Logout effettuato con successo.')
        logout(request)
    return redirect('home')


def register(request):
    if request.user.is_authenticated:
        return redirect('lotteries:list')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registrazione completata!')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Ci sono errori nel form.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def buyer_dashboard(request):
    """Buyer dashboard view with bids, statistics, and filters"""
    bids = Bid.objects.filter(bidder=request.user).select_related('auction').order_by('-placed_at')
    
    status_filter = request.GET.get('status', 'all')
    now = timezone.now()
    
    if status_filter == 'active':
        bids = bids.filter(auction__status__in=['active', 'ending'])
    elif status_filter == 'won':
        won_auctions = AuctionResult.objects.filter(winner=request.user, status='completed').values_list('auction_id')
        bids = bids.filter(auction_id__in=won_auctions, is_highest=True)
    elif status_filter == 'outbid':
        bids = bids.filter(status='outbid')
    
    # Statistics
    total_bids = Bid.objects.filter(bidder=request.user, status='completed').count()
    won_count = AuctionResult.objects.filter(winner=request.user, status='completed').count()
    outbid_count = Bid.objects.filter(bidder=request.user, status='outbid').count()
    total_spent = Payment.objects.filter(user=request.user, status='completed').aggregate(
        total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
    )['total']
    
    context = {
        'bids': bids,
        'status_filter': status_filter,
        'total_bids': total_bids,
        'won_auctions': won_count,
        'outbid_count': outbid_count,
        'total_spent': total_spent,
        'now': now,
    }
    return render(request, 'accounts/buyer_dashboard.html', context)


@login_required
def buyer_profile_edit(request):
    profile = Profile.objects.get_or_create(user=request.user)[0]
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        user_settings_form = UserSettingsForm(request.POST, instance=request.user)
        if profile_form.is_valid() and user_settings_form.is_valid():
            profile_form.save()
            user_settings_form.save()
            messages.success(request, 'Profilo aggiornato!')
            return redirect('accounts:buyer_dashboard')
    else:
        profile_form = ProfileForm(instance=profile)
        user_settings_form = UserSettingsForm(instance=request.user)
    return render(request, 'accounts/buyer_profile_edit.html', {'profile_form': profile_form, 'user_settings_form': user_settings_form})


@login_required
def buyer_change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password modificata!')
            return redirect('accounts:buyer_dashboard')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def settings(request):
    return render(request, 'accounts/settings.html')


def contact(request):
    return render(request, 'accounts/contact.html')


def privacy(request):
    return render(request, 'accounts/privacy.html')


@login_required
def seller_dashboard(request):
    """Seller dashboard with auction management and statistics"""
    if not request.user.auctions_as_seller.exists():
        return redirect('accounts:seller_create_lottery')
    
    seller_auctions = (
        Auction.objects.filter(seller=request.user)
        .annotate(bids_count=Count('bids', distinct=True))
        .order_by('-created_at')
    )
    
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        seller_auctions = seller_auctions.filter(status__in=['active', 'ending'])
    elif status_filter == 'closed':
        seller_auctions = seller_auctions.filter(status__in=['closed', 'completed'])
    
    # Calculate statistics
    completed_bids = Bid.objects.filter(auction__seller=request.user, status='completed')
    total_bids_received = completed_bids.count()
    
    total_earnings = PaymentTransaction.objects.filter(
        ticket__auction__seller=request.user, status='completed'
    ).aggregate(total_net=Coalesce(Sum('net_amount'), 0, output_field=DecimalField()))['total_net']
    
    total_auctions_created = request.user.auctions_as_seller.count()
    
    # Recent activity
    recent_bids = completed_bids.select_related('auction', 'bidder').order_by('-placed_at')[:5]
    
    kyc_status = {
        'is_verified': request.user.is_verified,
        'status_display': 'Approvato' if request.user.is_verified else 'In attesa',
        'can_create_auction': request.user.is_verified,
    }
    
    context = {
        'seller_lotteries': seller_auctions,
        'status_filter': status_filter,
        'total_auctions_created': total_auctions_created,
        'total_bids_received': total_bids_received,
        'total_earnings': total_earnings,
        'recent_sales': recent_bids,
        'kyc_status': kyc_status,
    }
    return render(request, 'accounts/seller_dashboard.html', context)


@login_required
def seller_create_lottery(request):
    """Create new auction"""
    if not request.user.is_verified:
        messages.error(request, 'Per creare aste devi completare la verifica KYC.')
        return redirect('accounts:seller_kyc_settings')
    
    if request.method == 'POST':
        form = AuctionCreationForm(request.POST, request.FILES)
        if form.is_valid():
            auction = form.save(commit=False)
            auction.seller = request.user
            auction.status = 'draft'
            try:
                auction.save()
                messages.success(request, f'Asta "{auction.title}" creata!')
                return redirect('accounts:seller_dashboard')
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Ci sono errori nel form.')
    else:
        form = AuctionCreationForm()
    return render(request, 'accounts/seller_create_lottery.html', {'form': form})


@login_required
def seller_lottery_detail(request, lottery_id):
    """Detail view for a specific auction with bid analytics"""
    auction = get_object_or_404(
        Auction.objects.annotate(bids_count=Count('bids')),
        id=lottery_id, seller=request.user
    )
    
    # Get all bids
    all_bids = Bid.objects.filter(auction=auction).select_related('bidder').order_by('-placed_at')
    
    # Calculate earnings
    total_bids_value = all_bids.filter(status='completed').aggregate(
        total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
    )['total']
    commission_rate = Decimal('0.10')
    net_earnings = total_bids_value * (1 - commission_rate)
    commission_amount = total_bids_value * commission_rate
    
    # Bid analytics by date
    bids_by_date = all_bids.filter(status='completed').annotate(
        date=TruncDate('placed_at')
    ).values('date').annotate(bids_count=Count('id'), revenue=Sum('amount')).order_by('date')
    
    bid_dates = [item['date'].strftime('%Y-%m-%d') for item in bids_by_date]
    bid_counts = [item['bids_count'] for item in bids_by_date]
    daily_revenues = [float(item['revenue'] or 0) for item in bids_by_date]
    
    # Get winner if auction is closed
    winner = None
    auction_result = None
    if auction.status == 'closed':
        auction_result = auction.results.filter(status='completed').first()
        if auction_result and auction_result.winner:
            winner = {'user': auction_result.winner, 'bid': auction_result.winning_bid, 'closed_at': auction_result.closed_at}
    
    # Check if can close manually
    can_close = False
    if auction.status == 'active' and auction.bids.exists():
        can_close = True

    context = {
        'lottery': auction,
        'all_bids': all_bids,
        'total_revenue': total_bids_value,
        'net_earnings': net_earnings,
        'commission_amount': commission_amount,
        'bid_dates': bid_dates,
        'bid_counts': bid_counts,
        'daily_revenues': daily_revenues,
        'winner': winner,
        'winner_drawing': auction_result,
        'can_close': can_close,
    }
    return render(request, 'accounts/seller_lottery_detail.html', context)


@login_required
def seller_reports(request):
    """Financial reports for seller with CSV download"""
    completed_bids = Bid.objects.filter(auction__seller=request.user, status='completed').select_related('auction', 'bidder')
    
    completed_transactions = PaymentTransaction.objects.filter(ticket__auction__seller=request.user, status='completed')
    
    total_gross = completed_transactions.aggregate(total=Coalesce(Sum('amount'), 0, output_field=DecimalField()))['total']
    total_commissions = completed_transactions.aggregate(total=Coalesce(Sum('commission'), 0, output_field=DecimalField()))['total']
    total_earnings = completed_transactions.aggregate(total=Coalesce(Sum('net_amount'), 0, output_field=DecimalField()))['total']
    
    auction_reports = Auction.objects.filter(seller=request.user).annotate(
        total_bids=Count('bids', distinct=True),
        gross_revenue=Coalesce(Sum('bids__amount', filter=Q(bids__status='completed')), Decimal('0.00'), output_field=DecimalField(max_digits=15, decimal_places=2)),
    ).filter(total_bids__gt=0).order_by('-created_at')
    
    if request.GET.get('download') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="seller_report_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Data Report', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['RIEPILOGO TOTALE'])
        writer.writerow(['Metrica', 'Valore'])
        writer.writerow(['Fatturato Totale', f'€ {total_gross:.2f}' if total_gross else '€ 0.00'])
        writer.writerow(['Commissioni', f'€ {total_commissions:.2f}' if total_commissions else '€ 0.00'])
        writer.writerow(['Guadagno Netto', f'€ {total_earnings:.2f}' if total_earnings else '€ 0.00'])
        writer.writerow(['Offerte Ricevute', completed_bids.count()])
        writer.writerow(['Numero Aste', request.user.auctions_as_seller.count()])
        return response
    
    context = {'total_gross': total_gross, 'total_commissions': total_commissions, 'total_earnings': total_earnings,
               'bids_received': completed_bids.count(), 'lottery_reports': auction_reports}
    return render(request, 'accounts/seller_reports.html', context)


@login_required
def seller_kyc_settings(request):
    kyc_info = {'is_verified': request.user.is_verified, 'status': 'Approvato' if request.user.is_verified else 'In attesa'}
    if request.method == 'POST':
        messages.info(request, 'Funzionalità in fase di implementazione.')
    return render(request, 'accounts/seller_kyc_settings.html', {'kyc_info': kyc_info})


@login_required
def mark_winner_as_shipped(request, drawing_id):
    """Mark auction prize as shipped"""
    result = get_object_or_404(AuctionResult, id=drawing_id)
    if request.user != result.auction.seller:
        messages.error(request, 'Non hai il permesso.')
        return redirect('accounts:seller_dashboard')
    if result.is_shipped:
        messages.warning(request, 'Già spedito.')
    else:
        result.mark_as_shipped()
        messages.success(request, 'Segnato come spedito!')
    return redirect('accounts:seller_lottery_detail', lottery_id=result.auction.id)
