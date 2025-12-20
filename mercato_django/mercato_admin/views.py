from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse


@staff_member_required
def dashboard(request):
    """
    Admin dashboard
    """
    return render(request, 'admin/dashboard.html')


@staff_member_required
def user_management(request):
    """
    User management page
    """
    return render(request, 'admin/users.html')


@staff_member_required
def lottery_management(request):
    """
    Lottery management page
    """
    return render(request, 'admin/lotteries.html')


@staff_member_required
def payment_management(request):
    """
    Payment management page
    """
    return render(request, 'admin/payments.html')


@staff_member_required
def site_settings(request):
    """
    Site settings page
    """
    return render(request, 'admin/settings.html')


@staff_member_required
def reports(request):
    """
    Reports page
    """
    return render(request, 'admin/reports.html')


@staff_member_required
def system_logs(request):
    """
    System logs page
    """
    return render(request, 'admin/logs.html')