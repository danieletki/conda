from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Notification, 
    EmailLog, 
    EmailNotification,
    PushNotification,
    NotificationSettings,
    NotificationCategory
)


@admin.register(NotificationCategory)
class NotificationCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'icon', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 3px; display: inline-block;"></div>',
            obj.color
        )
    color_display.short_description = 'Colore'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'category', 'is_read', 'priority', 'created_at']
    list_filter = ['notification_type', 'category', 'is_read', 'is_sent', 'priority', 'created_at']
    search_fields = ['title', 'message', 'user__username', 'user__email']
    readonly_fields = ['id', 'sent_at', 'read_at', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informazioni Base', {
            'fields': ('id', 'user', 'title', 'message')
        }),
        ('Configurazione', {
            'fields': ('notification_type', 'category', 'priority', 'action_url', 'action_text')
        }),
        ('Stato', {
            'fields': ('is_read', 'is_sent', 'scheduled_for', 'metadata')
        }),
        ('Timestamp', {
            'fields': ('sent_at', 'read_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'category')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['subject', 'recipient_email', 'user_display', 'template_used', 'status_badge', 'priority', 'retry_count', 'sent_at', 'created_at']
    list_filter = ['status', 'template_used', 'priority', 'provider', 'created_at', 'sent_at']
    search_fields = ['subject', 'recipient_email', 'user__username', 'user__email', 'error_message']
    readonly_fields = ['external_message_id', 'sent_at', 'delivered_at', 'created_at', 'updated_at', 'retry_count']
    date_hierarchy = 'created_at'
    actions = ['retry_failed_emails', 'mark_as_delivered', 'mark_as_failed']
    
    fieldsets = (
        ('Destinatario', {
            'fields': ('user', 'recipient_email', 'from_email')
        }),
        ('Contenuto Email', {
            'fields': ('subject', 'template_used', 'context_data')
        }),
        ('Stato Invio', {
            'fields': ('status', 'priority', 'provider', 'error_message', 'retry_count', 'max_retries')
        }),
        ('Tracking', {
            'fields': ('external_message_id', 'sent_at', 'delivered_at', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def user_display(self, obj):
        if obj.user:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:mercato_accounts_customuser_change', args=[obj.user.id]),
                obj.user.username
            )
        return '-'
    user_display.short_description = 'Utente'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'sent': '#28a745', 
            'delivered': '#20c997',
            'failed': '#dc3545',
            'bounced': '#fd7e14',
            'retry': '#ffc107'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Stato'
    
    def retry_failed_emails(self, request, queryset):
        """Retry failed emails"""
        from .email_service import EmailService
        
        email_service = EmailService()
        retried_count = 0
        
        for email_log in queryset.filter(status__in=['failed', 'retry']):
            if email_log.retry_email(email_service):
                retried_count += 1
        
        self.message_user(request, f'{retried_count} email sono state rimesse in coda per il retry.')
    retry_failed_emails.short_description = 'Riprova email fallite'
    
    def mark_as_delivered(self, request, queryset):
        """Mark emails as delivered"""
        count = queryset.count()
        for email_log in queryset:
            email_log.mark_as_delivered()
        self.message_user(request, f'{count} email sono state marcate come consegnate.')
    mark_as_delivered.short_description = 'Marca come consegnate'
    
    def mark_as_failed(self, request, queryset):
        """Mark emails as failed"""
        count = queryset.count()
        for email_log in queryset:
            email_log.mark_as_failed("Marcato manualmente dall'admin")
        self.message_user(request, f'{count} email sono state marcate come fallite.')
    mark_as_failed.short_description = 'Marca come fallite'


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ['notification', 'recipient_email', 'subject', 'status', 'provider', 'sent_at']
    list_filter = ['status', 'provider', 'sent_at', 'created_at']
    search_fields = ['recipient_email', 'subject', 'notification__title']
    readonly_fields = ['sent_at', 'delivered_at', 'created_at']
    date_hierarchy = 'sent_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification')


@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ['notification', 'platform', 'device_token_preview', 'status', 'sent_at']
    list_filter = ['platform', 'status', 'created_at', 'sent_at']
    search_fields = ['notification__title', 'device_token']
    readonly_fields = ['sent_at', 'created_at']
    
    def device_token_preview(self, obj):
        return obj.device_token[:20] + '...' if len(obj.device_token) > 20 else obj.device_token
    device_token_preview.short_description = 'Device Token'


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'push_enabled', 'sms_enabled', 'updated_at']
    list_filter = ['email_enabled', 'push_enabled', 'sms_enabled', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Utente', {
            'fields': ('user',)
        }),
        ('Preferenze Email', {
            'fields': ('email_enabled', 'email_lottery_results', 'email_new_lotteries', 
                      'email_payment_updates', 'email_system_updates')
        }),
        ('Preferenze Push', {
            'fields': ('push_enabled', 'push_lottery_results', 'push_new_lotteries', 
                      'push_payment_updates', 'push_system_updates')
        }),
        ('Preferenze SMS', {
            'fields': ('sms_enabled', 'sms_phone_number')
        }),
        ('Orari Silenziosi', {
            'fields': ('quiet_hours_start', 'quiet_hours_end')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
