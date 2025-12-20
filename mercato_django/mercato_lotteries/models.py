from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import signals
from django.urls import reverse
from decimal import Decimal
import base64
import uuid
from io import BytesIO
from PIL import Image
import logging
import os

User = get_user_model()
logger = logging.getLogger(__name__)


class CompressedImageField(models.BinaryField):
    """
    Custom field for storing compressed images as BLOB
    """
    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        kwargs['null'] = True
        super().__init__(*args, **kwargs)
    
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('blank', None)
        kwargs.pop('null', None)
        return name, path, args, kwargs


def compress_image(image_file, max_size=(1024, 1024), quality=85):
    """
    Compress image using Pillow and return as bytes
    """
    if not image_file:
        return None
    
    try:
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if larger than max_size
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to BytesIO with compression
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return None


class Lottery(models.Model):
    """
    Main lottery model with KYC validation and image compression
    """
    STATUS_CHOICES = [
        ('draft', 'Bozza'),
        ('active', 'Attiva'),
        ('closed', 'Chiusa'),
        ('drawn', 'Estrazione Eseguita'),
        ('completed', 'Completata'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    item_value = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    items_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lotteries_as_seller')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    kyc_completed = models.BooleanField(default=False)
    expiration_date = models.DateTimeField(null=True, blank=True)
    
    # Compressed images stored as BLOB
    image_1 = CompressedImageField()
    image_2 = CompressedImageField()
    image_3 = CompressedImageField()
    
    # Description for each image
    image_1_description = models.CharField(max_length=255, blank=True)
    image_2_description = models.CharField(max_length=255, blank=True)
    image_3_description = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_status_color(self):
        """Get bootstrap color class for status badge"""
        status_colors = {
            'draft': 'secondary',
            'active': 'success',
            'closed': 'info',
            'drawn': 'primary',
            'completed': 'dark'
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_status_display(self):
        """Get display name for status"""
        status_display = {
            'draft': 'Bozza',
            'active': 'Attiva',
            'closed': 'Chiusa',
            'drawn': 'Estrazione Eseguita',
            'completed': 'Completata'
        }
        return status_display.get(self.status, self.status)

    def get_absolute_url(self):
        return reverse('lotteries:detail', kwargs={'lottery_id': self.id})

    @property
    def tickets_sold(self):
        if hasattr(self, 'tickets_sold_count'):
            return self.tickets_sold_count
        return self.tickets.filter(payment_status='completed').count()

    @property
    def tickets_remaining(self):
        return max(self.items_count - self.tickets_sold, 0)

    @property
    def progress_percent(self):
        if not self.items_count:
            return 0
        return min(int((self.tickets_sold / self.items_count) * 100), 100)

    @property
    def main_image_data_uri(self):
        if not self.image_1:
            return None
        encoded = base64.b64encode(self.image_1).decode('ascii')
        return f"data:image/jpeg;base64,{encoded}"

    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.items_count
    
    def calculate_ticket_price(self):
        """Calculate ticket price as item_value / items_count"""
        if self.item_value and self.items_count:
            return round(self.item_value / Decimal(self.items_count), 2)
        return None
    
    def save(self, *args, **kwargs):
        # Calculate ticket price automatically
        if not self.ticket_price and self.item_value and self.items_count:
            self.ticket_price = self.calculate_ticket_price()
        
        # Check KYC validation before activating lottery
        if self.status == 'active' and not self.kyc_completed:
            # Check if seller is verified (is_verified field from CustomUser)
            if not getattr(self.seller, 'is_verified', False):
                raise ValidationError("Cannot activate lottery without KYC verification")
            self.kyc_completed = True
        
        # Handle image compression
        if hasattr(self, '_image_1_file'):
            self.image_1 = compress_image(self._image_1_file)
            self._image_1_file = None
        
        if hasattr(self, '_image_2_file'):
            self.image_2 = compress_image(self._image_2_file)
            self._image_2_file = None
            
        if hasattr(self, '_image_3_file'):
            self.image_3 = compress_image(self._image_3_file)
            self._image_3_file = None
        
        super().save(*args, **kwargs)
    
    def set_image_1(self, image_file):
        """Set image 1 with compression"""
        self._image_1_file = image_file
    
    def set_image_2(self, image_file):
        """Set image 2 with compression"""
        self._image_2_file = image_file
        
    def set_image_3(self, image_file):
        """Set image 3 with compression"""
        self._image_3_file = image_file
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['seller', 'status']),
        ]


class LotteryTicket(models.Model):
    """
    Individual lottery tickets
    """
    STATUS_CHOICES = [
        ('pending', 'In attesa'),
        ('payment_processing', 'Elaborazione pagamento'),
        ('payment_failed', 'Pagamento fallito'),
        ('completed', 'Completato'),
        ('refunded', 'Rimborsato'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE, related_name='tickets')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchased_tickets')
    ticket_number = models.CharField(max_length=20, unique=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    class Meta:
        unique_together = ['lottery', 'buyer', 'ticket_number']
        ordering = ['-purchased_at']
    
    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.lottery.title}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generate ticket number from lottery ID and sequential number
            last_ticket = self.lottery.tickets.order_by('-purchased_at').first()
            if last_ticket:
                try:
                    parts = last_ticket.ticket_number.split('-')
                    last_num = int(parts[-1]) if parts else 0
                except (ValueError, IndexError):
                    last_num = 0
            else:
                last_num = 0
            self.ticket_number = f"TICKET-{self.lottery.id}-{last_num + 1:04d}"
        super().save(*args, **kwargs)


class WinnerDrawing(models.Model):
    """
    Winner drawing record for lotteries
    """
    STATUS_CHOICES = [
        ('pending', 'In attesa'),
        ('completed', 'Completato'),
        ('cancelled', 'Annullato'),
    ]
    
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE, related_name='drawings')
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_lotteries')
    winning_ticket = models.ForeignKey(LotteryTicket, on_delete=models.SET_NULL, null=True, blank=True)
    drawn_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    prize_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ['-drawn_at']
        indexes = [
            models.Index(fields=['status', 'drawn_at']),
        ]
    
    def __str__(self):
        return f"Estrazione {self.lottery.title} - {self.drawn_at}"


# Django signals
def lottery_pre_save(sender, instance, **kwargs):
    """Check KYC validation and calculate ticket price"""
    if instance.status == 'active' and not instance.kyc_completed:
        # Check if seller is verified (is_verified field from CustomUser)
        if not getattr(instance.seller, 'is_verified', False):
            raise ValidationError("Cannot activate lottery: seller KYC verification required")
        instance.kyc_completed = True


def handle_lottery_fulfillment(sender, instance, created, **kwargs):
    """Set expiration date when lottery is fulfilled"""
    if instance.is_sold_out and not instance.expiration_date:
        instance.expiration_date = timezone.now() + timezone.timedelta(days=15)
        instance.status = 'closed'
        instance.save()


# Connect signals
signals.pre_save.connect(lottery_pre_save, sender=Lottery)
signals.post_save.connect(handle_lottery_fulfillment, sender=Lottery)