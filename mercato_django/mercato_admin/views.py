from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
import csv
import json
from datetime import datetime

from mercato_accounts.models import CustomUser, Profile
from mercato_lotteries.models import Lottery, LotteryTicket, WinnerDrawing
from mercato_payments.models import Payment, PaymentTransaction
from mercato_notifications.models import EmailLog
from mercato_notifications.email_service import EmailService
from .models import AdminActionLog, SiteBanner, KYCDocument


def log_admin_action(request, action_type, action_description, related_model=None, related_id=None, metadata=None):
    """Log admin actions for auditing"""
    if metadata is None:
        metadata = {}
    
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AdminActionLog.objects.create(
        admin_user=request.user,
        action_type=action_type,
        action_description=action_description,
        related_model=related_model,
        related_id=str(related_id) if related_id else None,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent
    )


@staff_member_required
def admin_dashboard(request):
    """
    Admin dashboard with statistics
    """
    # User statistics
    total_users = CustomUser.objects.count()
    verified_users = CustomUser.objects.filter(is_verified=True).count()
    unverified_users = total_users - verified_users
    
    # Lottery statistics
    total_lotteries = Lottery.objects.count()
    active_lotteries = Lottery.objects.filter(status='active').count()
    closed_lotteries = Lottery.objects.filter(status='closed').count()
    completed_lotteries = Lottery.objects.filter(status='completed').count()
    
    # Payment statistics
    total_payments = Payment.objects.count()
    completed_payments = Payment.objects.filter(status='completed').count()
    total_revenue = Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Commission statistics
    total_commissions = PaymentTransaction.objects.filter(status='completed').aggregate(Sum('commission'))['commission__sum'] or 0
    
    # Recent activities
    recent_users = CustomUser.objects.order_by('-created_at')[:5]
    recent_lotteries = Lottery.objects.order_by('-created_at')[:5]
    recent_payments = Payment.objects.filter(status='completed').order_by('-created_at')[:5]
    
    # KYC pending count
    kyc_pending_count = KYCDocument.objects.filter(status='pending').count()
    
    # Lotteries pending moderation
    lotteries_pending = Lottery.objects.filter(status='draft').count()
    
    context = {
        'total_users': total_users,
        'verified_users': verified_users,
        'unverified_users': unverified_users,
        'total_lotteries': total_lotteries,
        'active_lotteries': active_lotteries,
        'closed_lotteries': closed_lotteries,
        'completed_lotteries': completed_lotteries,
        'total_payments': total_payments,
        'completed_payments': completed_payments,
        'total_revenue': total_revenue,
        'total_commissions': total_commissions,
        'recent_users': recent_users,
        'recent_lotteries': recent_lotteries,
        'recent_payments': recent_payments,
        'kyc_pending_count': kyc_pending_count,
        'lotteries_pending': lotteries_pending,
    }
    
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def kyc_pending_list(request):
    """
    List of pending KYC documents
    """
    # Get all pending KYC documents
    kyc_documents = KYCDocument.objects.filter(status='pending').select_related('user').order_by('-uploaded_at')
    
    # Pagination
    paginator = Paginator(kyc_documents, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'kyc_documents': page_obj,
    }
    
    return render(request, 'admin/kyc_pending.html', context)


@staff_member_required
def kyc_approve(request, document_id):
    """
    Approve KYC document
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    kyc_document = get_object_or_404(KYCDocument, id=document_id, status='pending')
    notes = request.POST.get('notes', '')
    
    try:
        # Approve KYC document
        kyc_document.approve(request.user, notes)
        
        # Send approval email
        email_service = EmailService()
        email_service.send_kyc_approved_email(kyc_document.user)
        
        # Log action
        log_admin_action(
            request,
            'kyc_approve',
            f'KYC approved for user {kyc_document.user.username}',
            related_model='CustomUser',
            related_id=kyc_document.user.id,
            metadata={'document_id': str(kyc_document.id), 'notes': notes}
        )
        
        messages.success(request, f'KYC for {kyc_document.user.username} has been approved successfully!')
        return JsonResponse({'success': True, 'message': 'KYC approved successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def kyc_reject(request, document_id):
    """
    Reject KYC document
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    kyc_document = get_object_or_404(KYCDocument, id=document_id, status='pending')
    rejection_reason = request.POST.get('rejection_reason', '')
    notes = request.POST.get('notes', '')
    
    if not rejection_reason:
        return JsonResponse({'success': False, 'error': 'Rejection reason is required'}, status=400)
    
    try:
        # Reject KYC document
        kyc_document.reject(request.user, rejection_reason, notes)
        
        # Send rejection email
        email_service = EmailService()
        email_service.send_kyc_rejected_email(kyc_document.user, rejection_reason)
        
        # Log action
        log_admin_action(
            request,
            'kyc_reject',
            f'KYC rejected for user {kyc_document.user.username}',
            related_model='CustomUser',
            related_id=kyc_document.user.id,
            metadata={'document_id': str(kyc_document.id), 'rejection_reason': rejection_reason, 'notes': notes}
        )
        
        messages.success(request, f'KYC for {kyc_document.user.username} has been rejected successfully!')
        return JsonResponse({'success': True, 'message': 'KYC rejected successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def lottery_moderation_list(request):
    """
    List of lotteries pending moderation
    """
    # Get all draft lotteries (pending moderation)
    lotteries = Lottery.objects.filter(status='draft').select_related('seller').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(lotteries, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'lotteries': page_obj,
    }
    
    return render(request, 'admin/lottery_moderation.html', context)


@staff_member_required
def lottery_approve(request, lottery_id):
    """
    Approve lottery
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    lottery = get_object_or_404(Lottery, id=lottery_id, status='draft')
    
    try:
        # Check if seller is verified
        if not lottery.seller.is_verified:
            return JsonResponse({'success': False, 'error': 'Seller must be KYC verified to approve lottery'}, status=400)
        
        # Approve lottery
        lottery.status = 'active'
        lottery.kyc_completed = True
        lottery.save()
        
        # Send activation email to seller
        email_service = EmailService()
        email_service.send_lottery_activated_email(lottery.seller, lottery)
        
        # Log action
        log_admin_action(
            request,
            'lottery_approve',
            f'Lottery "{lottery.title}" approved',
            related_model='Lottery',
            related_id=lottery.id,
            metadata={'lottery_title': lottery.title, 'seller_id': lottery.seller.id}
        )
        
        messages.success(request, f'Lottery "{lottery.title}" has been approved successfully!')
        return JsonResponse({'success': True, 'message': 'Lottery approved successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def lottery_reject(request, lottery_id):
    """
    Reject lottery
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    lottery = get_object_or_404(Lottery, id=lottery_id, status='draft')
    rejection_reason = request.POST.get('rejection_reason', '')
    
    if not rejection_reason:
        return JsonResponse({'success': False, 'error': 'Rejection reason is required'}, status=400)
    
    try:
        # Reject lottery (set to cancelled status)
        lottery.status = 'cancelled'
        lottery.save()
        
        # Send rejection notification to seller
        # Note: We could send an email here, but for now we'll just log it
        
        # Log action
        log_admin_action(
            request,
            'lottery_reject',
            f'Lottery "{lottery.title}" rejected',
            related_model='Lottery',
            related_id=lottery.id,
            metadata={'lottery_title': lottery.title, 'seller_id': lottery.seller.id, 'rejection_reason': rejection_reason}
        )
        
        messages.success(request, f'Lottery "{lottery.title}" has been rejected successfully!')
        return JsonResponse({'success': True, 'message': 'Lottery rejected successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def payment_reports(request):
    """
    Payment reports and statistics
    """
    # Get all payments with filtering
    payments = Payment.objects.select_related('user', 'payment_method').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        payments = payments.filter(created_at__gte=start_date)
    if end_date:
        payments = payments.filter(created_at__lte=end_date)
    
    # Statistics
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    total_commissions = PaymentTransaction.objects.filter(payment__in=payments).aggregate(Sum('commission'))['commission__sum'] or 0
    
    # Pagination
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'payments': page_obj,
        'total_amount': total_amount,
        'total_commissions': total_commissions,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin/payment_reports.html', context)


@staff_member_required
def disputes_list(request):
    """
    Disputes and reports section (for future implementation)
    """
    context = {
        'disputes': [],  # Placeholder for future implementation
    }
    
    return render(request, 'admin/disputes.html', context)


@staff_member_required
def export_csv(request, export_type):
    """
    Export data as CSV
    """
    if export_type not in ['users', 'lotteries', 'payments']:
        return HttpResponse('Invalid export type', status=400)
    
    # Set up CSV response
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{export_type}_export_{timestamp}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Log the export action
    log_admin_action(
        request,
        'csv_export',
        f'Exported {export_type} data as CSV',
        related_model=export_type.capitalize(),
        metadata={'export_type': export_type, 'filename': filename}
    )
    
    if export_type == 'users':
        # Export users
        writer.writerow(['ID', 'Username', 'Email', 'First Name', 'Last Name', 'Phone', 'Date of Birth', 'Verified', 'Created At'])
        
        users = CustomUser.objects.all().select_related('profile')
        for user in users:
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                user.phone_number,
                user.date_of_birth,
                user.is_verified,
                user.created_at,
            ])
    
    elif export_type == 'lotteries':
        # Export lotteries
        writer.writerow(['ID', 'Title', 'Description', 'Item Value', 'Items Count', 'Ticket Price', 'Seller', 'Status', 'KYC Completed', 'Created At'])
        
        lotteries = Lottery.objects.all().select_related('seller')
        for lottery in lotteries:
            writer.writerow([
                lottery.id,
                lottery.title,
                lottery.description,
                lottery.item_value,
                lottery.items_count,
                lottery.ticket_price,
                lottery.seller.username,
                lottery.status,
                lottery.kyc_completed,
                lottery.created_at,
            ])
    
    elif export_type == 'payments':
        # Export payments
        writer.writerow(['ID', 'User', 'Amount', 'Currency', 'Status', 'Payment Method', 'Created At', 'Processed At'])
        
        payments = Payment.objects.all().select_related('user', 'payment_method')
        for payment in payments:
            writer.writerow([
                payment.id,
                payment.user.username,
                payment.amount,
                payment.currency,
                payment.status,
                payment.payment_method.name,
                payment.created_at,
                payment.processed_at,
            ])
    
    return response


@staff_member_required
def banner_management(request):
    """
    Manage site banners and announcements
    """
    banners = SiteBanner.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        if 'create_banner' in request.POST:
            return create_banner(request)
        elif 'update_banner' in request.POST:
            return update_banner(request)
        elif 'delete_banner' in request.POST:
            return delete_banner(request)
    
    context = {
        'banners': banners,
    }
    
    return render(request, 'admin/banner_management.html', context)


def create_banner(request):
    """Create a new banner"""
    title = request.POST.get('title', '')
    content = request.POST.get('content', '')
    banner_type = request.POST.get('banner_type', 'info')
    position = request.POST.get('position', 'top')
    is_active = request.POST.get('is_active', 'on') == 'on'
    link_url = request.POST.get('link_url', '')
    link_text = request.POST.get('link_text', '')
    
    if not title or not content:
        messages.error(request, 'Title and content are required')
        return redirect('admin_panel:banner_management')
    
    try:
        banner = SiteBanner.objects.create(
            title=title,
            content=content,
            banner_type=banner_type,
            position=position,
            is_active=is_active,
            link_url=link_url,
            link_text=link_text,
            created_by=request.user
        )
        
        # Log action
        log_admin_action(
            request,
            'banner_create',
            f'Banner "{title}" created',
            related_model='SiteBanner',
            related_id=banner.id,
            metadata={'title': title, 'banner_type': banner_type, 'position': position}
        )
        
        messages.success(request, 'Banner created successfully!')
        return redirect('admin_panel:banner_management')
        
    except Exception as e:
        messages.error(request, f'Error creating banner: {str(e)}')
        return redirect('admin_panel:banner_management')


def update_banner(request):
    """Update an existing banner"""
    banner_id = request.POST.get('banner_id')
    banner = get_object_or_404(SiteBanner, id=banner_id)
    
    title = request.POST.get('title', '')
    content = request.POST.get('content', '')
    banner_type = request.POST.get('banner_type', 'info')
    position = request.POST.get('position', 'top')
    is_active = request.POST.get('is_active', 'on') == 'on'
    link_url = request.POST.get('link_url', '')
    link_text = request.POST.get('link_text', '')
    
    if not title or not content:
        messages.error(request, 'Title and content are required')
        return redirect('admin_panel:banner_management')
    
    try:
        banner.title = title
        banner.content = content
        banner.banner_type = banner_type
        banner.position = position
        banner.is_active = is_active
        banner.link_url = link_url
        banner.link_text = link_text
        banner.save()
        
        # Log action
        log_admin_action(
            request,
            'banner_update',
            f'Banner "{title}" updated',
            related_model='SiteBanner',
            related_id=banner.id,
            metadata={'title': title, 'banner_type': banner_type, 'position': position}
        )
        
        messages.success(request, 'Banner updated successfully!')
        return redirect('admin_panel:banner_management')
        
    except Exception as e:
        messages.error(request, f'Error updating banner: {str(e)}')
        return redirect('admin_panel:banner_management')


def delete_banner(request):
    """Delete a banner"""
    banner_id = request.POST.get('banner_id')
    banner = get_object_or_404(SiteBanner, id=banner_id)
    
    try:
        banner_title = banner.title
        banner.delete()
        
        # Log action
        log_admin_action(
            request,
            'banner_delete',
            f'Banner "{banner_title}" deleted',
            related_model='SiteBanner',
            related_id=banner_id,
            metadata={'title': banner_title}
        )
        
        messages.success(request, 'Banner deleted successfully!')
        return redirect('admin_panel:banner_management')
        
    except Exception as e:
        messages.error(request, f'Error deleting banner: {str(e)}')
        return redirect('admin_panel:banner_management')


@staff_member_required
def admin_action_logs(request):
    """
    View admin action logs
    """
    # Get all admin action logs
    logs = AdminActionLog.objects.all().select_related('admin_user').order_by('-created_at')
    
    # Filter by action type
    action_type = request.GET.get('action_type')
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        logs = logs.filter(created_at__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__lte=end_date)
    
    # Pagination
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj,
        'action_type': action_type,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin/action_logs.html', context)