from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Max, Min, Q, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncDay
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.http import Http404
import csv
from datetime import datetime
from decimal import Decimal

from mercato_lotteries.models import Lottery, LotteryTicket, WinnerDrawing
from mercato_payments.models import Payment, PaymentTransaction
from mercato_lotteries.forms import LotteryCreationForm

from .forms import CustomUserCreationForm, CustomUserLoginForm, ProfileForm, UserSettingsForm, CustomPasswordChangeForm
from .models import CustomUser, Profile


def home(request):
    lotteries_qs = Lottery.objects.filter(status='active').annotate(
        tickets_sold_count=Count('tickets', filter=Q(tickets__payment_status='completed'))
    )

    featured_lotteries = lotteries_qs.order_by('-tickets_sold_count', '-created_at')[:3]
    latest_lotteries = lotteries_qs.order_by('-created_at')[:6]

    return render(
        request,
        'home.html',
        {
            'featured_lotteries': featured_lotteries,
            'latest_lotteries': latest_lotteries,
        },
    )


def login_view(request):
    """
    User login view
    """
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
    """
    User logout view
    """
    if request.user.is_authenticated:
        messages.success(request, 'Logout effettuato con successo.')
        logout(request)
    return redirect('home')


def register(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('lotteries:list')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registrazione completata con successo! Puoi ora effettuare il login.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Ci sono errori nel form. Correggi e riprova.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    """
    User profile view
    """
    return render(request, 'accounts/profile.html')


@login_required
def buyer_dashboard(request):
    """
    Buyer dashboard view with tickets, statistics, and filters
    """
    # Get all tickets for current user
    tickets = (
        LotteryTicket.objects.filter(buyer=request.user)
        .select_related('lottery')
        .order_by('-purchased_at')
    )
    
    # Filter by status if provided
    status_filter = request.GET.get('status', 'all')
    
    now = timezone.now()
    
    if status_filter == 'active':
        tickets = tickets.filter(
            Q(lottery__expiration_date__isnull=True) | Q(lottery__expiration_date__gt=now),
            lottery__status__in=['active', 'closed']
        )
    elif status_filter == 'expired':
        tickets = tickets.filter(
            Q(lottery__expiration_date__lte=now) |
            Q(lottery__status='completed')
        )
    elif status_filter == 'won':
        # Tickets for lotteries where this user won
        won_drawings = WinnerDrawing.objects.filter(
            winner=request.user,
            status='completed'
        ).values_list('winning_ticket_id', flat=True)
        tickets = tickets.filter(id__in=won_drawings)
    elif status_filter == 'lost':
        # Tickets from completed lotteries where user didn't win
        won_drawings = WinnerDrawing.objects.filter(
            status='completed'
        ).values_list('winning_ticket_id', flat=True)
        completed_tickets = tickets.filter(
            lottery__status='completed'
        ).exclude(id__in=won_drawings)
        tickets = completed_tickets
    
    # Calculate statistics
    all_user_tickets = LotteryTicket.objects.filter(
        buyer=request.user,
        payment_status='completed'
    )
    
    total_tickets = all_user_tickets.count()
    
    # Count won tickets
    won_count = WinnerDrawing.objects.filter(
        winner=request.user,
        status='completed'
    ).count()
    
    # Calculate total spent
    total_spent = (
        Payment.objects.filter(
            user=request.user,
            status='completed'
        ).aggregate(
            total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
        )['total']
    )
    
    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'total_tickets': total_tickets,
        'won_tickets': won_count,
        'total_spent': total_spent,
        'now': now,
    }
    
    return render(request, 'accounts/buyer_dashboard.html', context)


@login_required
def buyer_profile_edit(request):
    """
    Edit buyer profile (personal data and profile image)
    """
    profile = Profile.objects.get_or_create(user=request.user)[0]
    
    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        user_settings_form = UserSettingsForm(request.POST, instance=request.user)
        
        if profile_form.is_valid() and user_settings_form.is_valid():
            profile_form.save()
            user_settings_form.save()
            messages.success(request, 'Profilo aggiornato con successo!')
            return redirect('accounts:buyer_dashboard')
        else:
            messages.error(request, 'Ci sono errori nel form. Correggi e riprova.')
    else:
        profile_form = ProfileForm(instance=profile)
        user_settings_form = UserSettingsForm(instance=request.user)
    
    context = {
        'profile_form': profile_form,
        'user_settings_form': user_settings_form,
    }
    return render(request, 'accounts/buyer_profile_edit.html', context)


@login_required
def buyer_change_password(request):
    """
    Change password view
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password modificata con successo!')
            return redirect('accounts:buyer_dashboard')
        else:
            messages.error(request, 'Ci sono errori nel form. Correggi e riprova.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def settings(request):
    """
    User settings view
    """
    return render(request, 'accounts/settings.html')


def contact(request):
    """
    Contact page view
    """
    return render(request, 'accounts/contact.html')


def privacy(request):
    """
    Privacy policy page view
    """
    return render(request, 'accounts/privacy.html')


@login_required
def seller_dashboard(request):
    """
    Seller dashboard with lottery management, statistics, and reports
    """
    # Check if user is a seller (has lotteries created)
    if not request.user.lotteries_as_seller.exists():
        # Redirect to create lottery if no lotteries exist
        return redirect('accounts:seller_create_lottery')
    
    # Get seller's lotteries with statistics
    seller_lotteries = (
        Lottery.objects.filter(seller=request.user)
        .annotate(
            tickets_sold_count=Count(
                'tickets',
                filter=Q(tickets__payment_status='completed'),
                distinct=True,
            ),
            winning_drawings=Count(
                'drawings',
                filter=Q(drawings__status='completed'),
                distinct=True,
            ),
        )
        .annotate(
            total_revenue=ExpressionWrapper(
                Coalesce(F('ticket_price'), Decimal('0.00')) * F('tickets_sold_count'),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )
        .order_by('-created_at')
    )
    
    # Filter by status if provided
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        seller_lotteries = seller_lotteries.filter(status='active')
    elif status_filter == 'archived':
        seller_lotteries = seller_lotteries.filter(
            status__in=['closed', 'completed', 'drawn']
        )
    elif status_filter == 'won':
        seller_lotteries = seller_lotteries.filter(
            winning_drawings__gt=0
        )
    
    # Calculate overall statistics
    completed_tickets = LotteryTicket.objects.filter(
        lottery__seller=request.user,
        payment_status='completed'
    )
    
    total_tickets_sold = completed_tickets.count()
    
    # Calculate total earnings (net revenue after commission)
    total_earnings = PaymentTransaction.objects.filter(
        ticket__lottery__seller=request.user,
        status='completed'
    ).aggregate(
        total_net=Coalesce(Sum('net_amount'), 0, output_field=DecimalField())
    )['total_net']
    
    # Count total lotteries created
    total_lotteries_created = request.user.lotteries_as_seller.count()
    
    # Get recent activity (last 5 tickets sold)
    recent_sales = completed_tickets.select_related(
        'lottery', 'buyer'
    ).order_by('-purchased_at')[:5]
    
    # Check KYC status
    kyc_status = {
        'is_verified': request.user.is_verified,
        'status_display': 'Approvato' if request.user.is_verified else 'In attesa di approvazione',
        'can_create_lottery': request.user.is_verified,
    }
    
    context = {
        'seller_lotteries': seller_lotteries,
        'status_filter': status_filter,
        'total_lotteries_created': total_lotteries_created,
        'total_tickets_sold': total_tickets_sold,
        'total_earnings': total_earnings,
        'recent_sales': recent_sales,
        'kyc_status': kyc_status,
    }
    
    return render(request, 'accounts/seller_dashboard.html', context)


@login_required
def seller_create_lottery(request):
    """
    Create new lottery with image uploads
    """
    # Check KYC verification before allowing lottery creation
    if not request.user.is_verified:
        messages.error(
            request,
            'Per creare lotterie è necessario completare la verifica KYC. '
            'Carica i tuoi documenti nelle impostazioni KYC.'
        )
        return redirect('accounts:seller_kyc_settings')
    
    if request.method == 'POST':
        form = LotteryCreationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the lottery with the current user as seller
            lottery = form.save(commit=False)
            lottery.seller = request.user
            lottery.status = 'draft'  # Start as draft
            
            try:
                lottery.save()
                messages.success(
                    request,
                    f'Lotteria "{lottery.title}" creata con successo. '
                    'Puoi attivarla quando sei pronto.'
                )
                return redirect('accounts:seller_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Ci sono errori nel form. Correggi e riprova.')
    else:
        form = LotteryCreationForm()
    
    return render(request, 'accounts/seller_create_lottery.html', {
        'form': form,
    })


@login_required
def seller_lottery_detail(request, lottery_id):
    """
    Detail view for a specific lottery with sales analytics
    """
    lottery = get_object_or_404(
        Lottery.objects.annotate(
            tickets_sold_count=Count('tickets', filter=Q(tickets__payment_status='completed')),
            tickets_sold_value=Sum(
                'ticket_price',
                filter=Q(tickets__payment_status='completed')
            )
        ),
        id=lottery_id,
        seller=request.user
    )
    
    # Get completed tickets with buyer info
    completed_tickets = (
        LotteryTicket.objects.filter(
            lottery=lottery,
            payment_status='completed'
        )
        .select_related('buyer')
        .order_by('-purchased_at')
    )
    
    # Calculate net earnings (after commission)
    total_revenue = lottery.tickets_sold_value or 0
    commission_rate = Decimal('0.10')  # 10% commission
    net_earnings = total_revenue * (1 - commission_rate)
    commission_amount = total_revenue * commission_rate
    
    # Sales analytics - tickets sold per day
    sales_by_date = (
        completed_tickets
        .annotate(date=TruncDate('purchased_at'))
        .values('date')
        .annotate(
            tickets_count=Count('id'),
            revenue=Sum('lottery__ticket_price')
        )
        .order_by('date')
    )
    
    # Prepare data for charts
    sales_dates = [item['date'].strftime('%Y-%m-%d') for item in sales_by_date]
    sales_counts = [item['tickets_count'] for item in sales_by_date]
    daily_revenues = [float(item['revenue'] or 0) for item in sales_by_date]
    
    # Get winner if lottery is completed
    winner = None
    if lottery.status in ['drawn', 'completed']:
        winner_drawing = lottery.drawings.filter(status='completed').first()
        if winner_drawing:
            winner = {
                'user': winner_drawing.winner,
                'ticket': winner_drawing.winning_ticket,
                'drawn_at': winner_drawing.drawn_at,
            }
    
    context = {
        'lottery': lottery,
        'completed_tickets': completed_tickets,
        'total_revenue': total_revenue,
        'net_earnings': net_earnings,
        'commission_amount': commission_amount,
        'sales_dates': sales_dates,
        'sales_counts': sales_counts,
        'daily_revenues': daily_revenues,
        'winner': winner,
    }
    
    return render(request, 'accounts/seller_lottery_detail.html', context)


@login_required
def seller_reports(request):
    """
    Financial reports for seller with CSV download
    """
    # Get all completed payments for seller's lotteries
    completed_tickets = LotteryTicket.objects.filter(
        lottery__seller=request.user,
        payment_status='completed'
    ).select_related('lottery', 'buyer')
    
    # Calculate totals from payment transactions
    completed_transactions = PaymentTransaction.objects.filter(
        ticket__lottery__seller=request.user,
        status='completed'
    )
    
    total_gross = completed_transactions.aggregate(
        total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
    )['total']
    
    total_commissions = completed_transactions.aggregate(
        total=Coalesce(Sum('commission'), 0, output_field=DecimalField())
    )['total']
    
    total_earnings = completed_transactions.aggregate(
        total=Coalesce(Sum('net_amount'), 0, output_field=DecimalField())
    )['total']
    
    # Reports by lottery
    lottery_reports = (
        Lottery.objects.filter(seller=request.user)
        .annotate(
            tickets_sold=Count(
                'tickets',
                filter=Q(tickets__payment_status='completed'),
                distinct=True,
            ),
            gross_revenue=Coalesce(
                Sum(
                    'tickets__payment_transactions__amount',
                    filter=Q(tickets__payment_transactions__status='completed'),
                ),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            commission_amount=Coalesce(
                Sum(
                    'tickets__payment_transactions__commission',
                    filter=Q(tickets__payment_transactions__status='completed'),
                ),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            net_revenue=Coalesce(
                Sum(
                    'tickets__payment_transactions__net_amount',
                    filter=Q(tickets__payment_transactions__status='completed'),
                ),
                Decimal('0.00'),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
        )
        .filter(tickets_sold__gt=0)
        .order_by('-created_at')
    )
    
    # CSV Download
    if request.GET.get('download') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="seller_report_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Data Report',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        writer.writerow([])
        
        # Summary section
        writer.writerow(['RIEPILOGO TOTALE'])
        writer.writerow(['Metrica', 'Valore'])
        writer.writerow(['Fatturato Totale (Lordo)', f'€ {total_gross:.2f}' if total_gross else '€ 0.00'])
        writer.writerow(['Commissioni Totali', f'€ {total_commissions:.2f}' if total_commissions else '€ 0.00'])
        writer.writerow(['Guadagno Netto', f'€ {total_earnings:.2f}' if total_earnings else '€ 0.00'])
        writer.writerow(['Biglietti Venduti', completed_tickets.count()])
        writer.writerow(['Numero Lotterie', request.user.lotteries_as_seller.count()])
        writer.writerow([])
        
        # Detailed lottery breakdown
        writer.writerow(['DETTAGLIO PER LOTTERIA'])
        writer.writerow([
            'Titolo Lotteria',
            'Data Creazione',
            'Status',
            'Biglietti Venduti',
            'Fatturato Lordo',
            'Commissioni',
            'Guadagno Netto'
        ])
        
        for lottery in lottery_reports:
            writer.writerow([
                lottery.title,
                lottery.created_at.strftime('%Y-%m-%d'),
                lottery.get_status_display(),
                lottery.tickets_sold,
                f'€ {lottery.gross_revenue:.2f}',
                f'€ {lottery.commission_amount:.2f}',
                f'€ {lottery.net_revenue:.2f}'
            ])
        
        return response
    
    context = {
        'total_gross': total_gross,
        'total_commissions': total_commissions,
        'total_earnings': total_earnings,
        'tickets_sold': completed_tickets.count(),
        'lottery_reports': lottery_reports,
    }
    
    return render(request, 'accounts/seller_reports.html', context)


@login_required
def seller_kyc_settings(request):
    """
    KYC settings for sellers to upload/re-upload documents
    """
    # This is a placeholder - in a real implementation, you'd have a KYC document model
    # For now, we'll show the current KYC status and link to admin if needed
    
    kyc_info = {
        'is_verified': request.user.is_verified,
        'status': 'Approvato' if request.user.is_verified else 'In attesa',
        'submission_date': None,  # Would come from KYC document model
        'document_type': None,    # Would come from KYC document model
        'rejection_reason': None, # Would come from KYC document model
    }
    
    if request.method == 'POST':
        # In a real implementation, handle document upload here
        # For now, show a message that this would upload documents
        messages.info(
            request,
            'Funzionalità di upload documento in fase di implementazione. '
            'Contatta l\'amministratore per l\'upload manuale dei documenti.'
        )
        return redirect('accounts:seller_kyc_settings')
    
    context = {
        'kyc_info': kyc_info,
    }
    
    return render(request, 'accounts/seller_kyc_settings.html', context)