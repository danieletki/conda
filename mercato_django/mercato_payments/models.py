from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone

User = get_user_model()


class PaymentMethod(models.Model):
    """
    Payment methods (PayPal, Credit Cards, etc.)
    """
    METHOD_CHOICES = [
        ('paypal', 'PayPal'),
        ('credit_card', 'Carta di Credito'),
        ('bank_transfer', 'Bonifico Bancario'),
        ('crypto', 'Cryptovaluta'),
    ]
    
    name = models.CharField(max_length=50)
    method_type = models.CharField(max_length=20, choices=METHOD_CHOICES)
    is_active = models.BooleanField(default=True)
    processing_fee = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Payment(models.Model):
    """
    Payment records
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('completed', 'Completato'),
        ('failed', 'Fallito'),
        ('refunded', 'Rimborsato'),
        ('cancelled', 'Cancellato'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    currency = models.CharField(max_length=3, default='EUR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    paypal_order_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.user.username} - {self.amount} {self.currency}"
    
    def get_status_color(self):
        """Get bootstrap color class for status badge"""
        status_colors = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'info',
            'cancelled': 'secondary'
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_status_display(self):
        """Get display name for status"""
        status_display = {
            'pending': 'In Attesa',
            'completed': 'Completato',
            'failed': 'Fallito',
            'refunded': 'Rimborsato',
            'cancelled': 'Cancellato'
        }
        return status_display.get(self.status, self.status)

    @property
    def processing_fee_amount(self):
        """Calculate processing fee amount"""
        fee_percentage = self.payment_method.processing_fee / 100
        return (self.amount * fee_percentage).quantize(Decimal('0.01'))

    @property
    def net_amount(self):
        """Get net amount after processing fees"""
        return self.amount - self.processing_fee_amount

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['external_transaction_id']),
        ]


class LotteryPayment(models.Model):
    """
    Payment records specifically for lottery tickets
    """
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='lottery_payment')
    lottery = models.ForeignKey('mercato_lotteries.Lottery', on_delete=models.CASCADE)
    ticket_count = models.PositiveIntegerField()
    ticket_ids = models.JSONField(default=list)  # Store ticket IDs as array
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lottery Payment: {self.payment.id} - {self.ticket_count} tickets"


class Refund(models.Model):
    """
    Refund records
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('completed', 'Completato'),
        ('failed', 'Fallito'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    refund_amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_refund_id = models.CharField(max_length=100, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund {self.id} - {self.refund_amount} EUR"


class PaymentSettings(models.Model):
    """
    Payment system settings
    """
    paypal_client_id = models.CharField(max_length=200, blank=True)
    paypal_client_secret = models.CharField(max_length=200, blank=True)
    paypal_sandbox_mode = models.BooleanField(default=True)
    minimum_withdrawal = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
    processing_time_hours = models.PositiveIntegerField(default=24)
    auto_refund_enabled = models.BooleanField(default=False)
    currency = models.CharField(max_length=3, default='EUR')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Settings'
        verbose_name_plural = 'Payment Settings'

    def __str__(self):
        return f"Payment Settings ({'Sandbox' if self.paypal_sandbox_mode else 'Live'})"


class PaymentTransaction(models.Model):
    """
    Payment transaction model with commission calculation
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('processing', 'Elaborazione'),
        ('completed', 'Completato'),
        ('failed', 'Fallito'),
        ('refunded', 'Rimborsato'),
        ('cancelled', 'Cancellato'),
    ]
    
    COMMISSION_RATE = Decimal('0.10')  # 10% commission
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey('mercato_lotteries.LotteryTicket', on_delete=models.CASCADE, related_name='payment_transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    commission = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paypal_tx_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional payment details
    paypal_order_id = models.CharField(max_length=100, null=True, blank=True)
    paypal_payer_id = models.CharField(max_length=100, null=True, blank=True)
    payer_email = models.EmailField(max_length=254, null=True, blank=True)
    paypal_fee_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='EUR')
    
    # Store all ticket IDs for this transaction (when buying multiple tickets)
    ticket_ids = models.JSONField(default=list, blank=True)
    
    # Timestamps for status changes
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', 'status']),
            models.Index(fields=['paypal_tx_id']),
            models.Index(fields=['paypal_order_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Transaction {self.id} - Ticket {self.ticket.id} - {self.amount} EUR"
    
    def calculate_commission_and_net(self):
        """Calculate 10% commission and net amount"""
        self.commission = (self.amount * self.COMMISSION_RATE).quantize(Decimal('0.01'))
        self.net_amount = self.amount - self.commission
    
    def save(self, *args, **kwargs):
        """Override save to calculate commission automatically"""
        if not self.commission or self.commission == 0:
            self.calculate_commission_and_net()
        super().save(*args, **kwargs)
    
    def mark_as_completed(self):
        """Mark transaction as completed and update ticket status"""
        from django.db import transaction
        
        with transaction.atomic():
            self.status = 'completed'
            self.payment_completed_at = timezone.now()
            self.save()
            
            # Update ticket status
            self.ticket.payment_status = 'completed'
            self.ticket.save()
    
    def mark_as_refunded(self):
        """Mark transaction as refunded and update ticket status"""
        from django.db import transaction
        
        with transaction.atomic():
            self.status = 'refunded'
            self.refunded_at = timezone.now()
            self.save()
            
            # Update ticket status
            self.ticket.payment_status = 'refunded'
            self.ticket.save()
