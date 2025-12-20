from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Notification, NotificationSettings


@login_required
def notification_list(request):
    """
    Display user's notifications
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by read/unread status
    status = request.GET.get('status')
    if status == 'read':
        notifications = notifications.filter(is_read=True)
    elif status == 'unread':
        notifications = notifications.filter(is_read=False)
    
    return render(request, 'notifications/list.html', {
        'notifications': notifications
    })


@login_required
@require_POST
def mark_as_read(request, notification_id):
    """
    Mark a notification as read
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def mark_all_read(request):
    """
    Mark all user notifications as read
    """
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, 
        read_at=timezone.now()
    )
    return JsonResponse({'status': 'success'})


@login_required
def notification_settings(request):
    """
    User notification settings
    """
    settings, created = NotificationSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Handle form submission
        # This will be implemented with proper form handling
        pass
    
    return render(request, 'notifications/settings.html', {
        'settings': settings
    })