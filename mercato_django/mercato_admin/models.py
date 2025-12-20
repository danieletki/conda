from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = get_user_model()


class AdminSettings(models.Model):
    """
    Global admin settings for the platform
    """
    site_name = models.CharField(max_length=100, default='MercatoPro')
    site_description = models.TextField(blank=True)
    contact_email = models.EmailField()
    support_phone = models.CharField(max_length=20, blank=True)
    maintenance_mode = models.BooleanField(default=False)
    registration_enabled = models.BooleanField(default=True)
    max_tickets_per_lottery = models.PositiveIntegerField(default=10000)
    default_ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=22.00)
    currency = models.CharField(max_length=3, default='EUR')
    timezone = models.CharField(max_length=50, default='Europe/Rome')
    terms_of_service = models.TextField(blank=True)
    privacy_policy = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Admin Settings'
        verbose_name_plural = 'Admin Settings'

    def __str__(self):
        return f"Site Settings - {self.site_name}"


class SystemLog(models.Model):
    """
    System activity logs for admin monitoring
    """
    LOG_LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    ACTION_CHOICES = [
        ('user_registered', 'User Registered'),
        ('user_login', 'User Login'),
        ('lottery_created', 'Lottery Created'),
        ('lottery_ended', 'Lottery Ended'),
        ('payment_processed', 'Payment Processed'),
        ('ticket_purchased', 'Ticket Purchased'),
        ('notification_sent', 'Notification Sent'),
        ('admin_action', 'Admin Action'),
        ('system_event', 'System Event'),
    ]
    
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES, default='INFO')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default='system_event')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='system_logs')
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.level}] {self.action} - {self.user} - {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['level', 'created_at']),
        ]


class SiteStatistics(models.Model):
    """
    Site statistics for dashboard
    """
    date = models.DateField(unique=True)
    total_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    total_lotteries = models.PositiveIntegerField(default=0)
    active_lotteries = models.PositiveIntegerField(default=0)
    total_tickets_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_payments = models.PositiveIntegerField(default=0)
    successful_payments = models.PositiveIntegerField(default=0)
    total_notifications = models.PositiveIntegerField(default=0)
    sent_notifications = models.PositiveIntegerField(default=0)
    system_errors = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Statistics for {self.date}"

    @property
    def conversion_rate(self):
        """Calculate payment success rate"""
        if self.total_payments == 0:
            return 0
        return (self.successful_payments / self.total_payments) * 100

    class Meta:
        ordering = ['-date']


class Report(models.Model):
    """
    Admin-generated reports
    """
    REPORT_TYPE_CHOICES = [
        ('user_activity', 'User Activity Report'),
        ('lottery_performance', 'Lottery Performance'),
        ('financial_summary', 'Financial Summary'),
        ('payment_analysis', 'Payment Analysis'),
        ('notification_stats', 'Notification Statistics'),
        ('system_health', 'System Health Report'),
    ]
    
    TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom Period'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    period_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_reports')
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"

    class Meta:
        ordering = ['-created_at']


class Backup(models.Model):
    """
    Database backup management
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=100)
    file_path = models.FileField(upload_to='backups/', null=True, blank=True)
    file_size = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_backups')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.status}"

    class Meta:
        ordering = ['-created_at']
