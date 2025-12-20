from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Count, Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone

from mercato_lotteries.models import Lottery, LotteryTicket, WinnerDrawing
from mercato_payments.models import Payment, LotteryPayment

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