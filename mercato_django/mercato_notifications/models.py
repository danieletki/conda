from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class NotificationCategory(models.Model):
    """
    Categories for organizing notifications
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    icon = models.CharField(max_length=50, default='bell')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Notification(models.Model):
    """
    Main notification model
    """
    TYPE_CHOICES = [
        ('info', 'Informazione'),
        ('success', 'Successo'),
        ('warning', 'Avviso'),
        ('error', 'Errore'),
        ('lottery', 'Lotteria'),
        ('payment', 'Pagamento'),
        ('system', 'Sistema'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    category = models.ForeignKey(NotificationCategory, on_delete=models.CASCADE, related_name='notifications')
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Bassa'),
        ('normal', 'Normale'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ], default='normal')
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # For additional data
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def mark_as_sent(self):
        """Mark notification as sent"""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
            self.save()

    @property
    def is_scheduled(self):
        """Check if notification is scheduled for future"""
        return self.scheduled_for and self.scheduled_for > timezone.now()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['category', 'is_read']),
            models.Index(fields=['scheduled_for']),
        ]


class EmailNotification(models.Model):
    """
    Email notifications tracking
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('sent', 'Inviato'),
        ('delivered', 'Consegnato'),
        ('failed', 'Fallito'),
        ('bounced', 'Rimbalzato'),
    ]
    
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE, related_name='email_notification')
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_message_id = models.CharField(max_length=100, null=True, blank=True)
    provider = models.CharField(max_length=50, default='smtp')  # smtp, sendgrid, mailgun, etc.
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email: {self.notification.title} - {self.recipient_email}"


class PushNotification(models.Model):
    """
    Push notifications tracking
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('sent', 'Inviato'),
        ('delivered', 'Consegnato'),
        ('failed', 'Fallito'),
    ]
    
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE, related_name='push_notification')
    device_token = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=[
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    ])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_id = models.CharField(max_length=100, null=True, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Push: {self.notification.title} - {self.platform}"


class NotificationSettings(models.Model):
    """
    User notification preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_lottery_results = models.BooleanField(default=True)
    email_new_lotteries = models.BooleanField(default=True)
    email_payment_updates = models.BooleanField(default=True)
    email_system_updates = models.BooleanField(default=False)
    
    # Push preferences
    push_enabled = models.BooleanField(default=True)
    push_lottery_results = models.BooleanField(default=True)
    push_new_lotteries = models.BooleanField(default=True)
    push_payment_updates = models.BooleanField(default=True)
    push_system_updates = models.BooleanField(default=False)
    
    # SMS preferences (for future implementation)
    sms_enabled = models.BooleanField(default=False)
    sms_phone_number = models.CharField(max_length=17, blank=True)
    
    quiet_hours_start = models.TimeField(null=True, blank=True)  # e.g., 22:00
    quiet_hours_end = models.TimeField(null=True, blank=True)   # e.g., 08:00
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification Settings - {self.user.username}"

    class Meta:
        verbose_name = 'Notification Settings'
        verbose_name_plural = 'Notification Settings'
