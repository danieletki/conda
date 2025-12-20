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


class EmailLog(models.Model):
    """
    Email log for tracking all sent emails
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('sent', 'Inviato'),
        ('delivered', 'Consegnato'),
        ('failed', 'Fallito'),
        ('bounced', 'Rimbalzato'),
        ('retry', 'In Retry'),
    ]
    
    TEMPLATE_CHOICES = [
        ('registration', 'Registrazione'),
        ('kyc_approved', 'KYC Approvato'),
        ('kyc_rejected', 'KYC Rifiutato'),
        ('lottery_activated', 'Lotteria Attivata'),
        ('ticket_purchased', 'Biglietto Acquistato'),
        ('lottery_won', 'Vincita Lotteria'),
        ('seller_winner_notification', 'Notifica Venditore Vincitore'),
        ('lottery_lost', 'Perdita Lotteria'),
        ('expiration_reminder', 'Promemoria Scadenza'),
        ('custom', 'Personalizzato'),
    ]
    
    # User and recipient info
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='email_logs')
    recipient_email = models.EmailField()
    from_email = models.EmailField(default='')
    
    # Email content
    subject = models.CharField(max_length=200)
    template_used = models.CharField(max_length=50, choices=TEMPLATE_CHOICES, default='custom')
    context_data = models.JSONField(default=dict, blank=True)  # Store template context
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=[
        ('low', 'Bassa'),
        ('normal', 'Normale'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ], default='normal')
    
    # Provider info
    provider = models.CharField(max_length=50, default='smtp')  # smtp, sendgrid, mailgun, etc.
    external_message_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Email: {self.subject} - {self.recipient_email}"
    
    def mark_as_sent(self):
        """Mark email as sent"""
        if self.status in ['pending', 'retry']:
            self.status = 'sent'
            self.sent_at = timezone.now()
            self.retry_count = 0
            self.save()
    
    def mark_as_failed(self, error_message=None):
        """Mark email as failed"""
        self.status = 'failed'
        if error_message:
            self.error_message = error_message
        
        if self.retry_count < self.max_retries:
            self.status = 'retry'
            self.retry_count += 1
        
        self.save()
    
    def mark_as_delivered(self):
        """Mark email as delivered"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save()
    
    def should_retry(self):
        """Check if email should be retried"""
        return self.status in ['failed', 'retry'] and self.retry_count < self.max_retries
    
    def retry_email(self, email_service):
        """Retry sending the email"""
        if not self.should_retry():
            return False
        
        try:
            # Update status
            self.status = 'pending'
            self.error_message = ''
            self.save()
            
            # Retry sending
            success = email_service.send_email(
                template_name=self.template_used,
                recipient_email=self.recipient_email,
                subject=self.subject,
                context=self.context_data,
                from_email=self.from_email,
                user=self.user,
                priority=self.priority
            )
            
            if success:
                self.mark_as_sent()
                return True
            else:
                self.mark_as_failed("Retry failed")
                return False
                
        except Exception as e:
            self.mark_as_failed(str(e))
            return False
    
    @classmethod
    def create_log_entry(cls, template_name, recipient_email, subject, context_data=None, 
                        user=None, from_email=None, priority='normal'):
        """Create a new email log entry"""
        if context_data is None:
            context_data = {}
        
        return cls.objects.create(
            template_used=template_name,
            recipient_email=recipient_email,
            subject=subject,
            context_data=context_data,
            user=user,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            priority=priority
        )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['template_used', 'status']),
            models.Index(fields=['recipient_email', 'status']),
        ]


# Keep old EmailNotification for backward compatibility but deprecate it
class EmailNotification(models.Model):
    """
    DEPRECATED: Use EmailLog instead
    Email notifications tracking (legacy)
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
