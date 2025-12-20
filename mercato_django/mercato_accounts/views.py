from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse

from mercato_lotteries.models import Lottery

from .forms import CustomUserCreationForm, CustomUserLoginForm
from .models import CustomUser


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