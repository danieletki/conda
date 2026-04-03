import base64
import logging
import uuid
from decimal import Decimal
from io import BytesIO
from datetime import timedelta

from PIL import Image

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import signals
from django.urls import reverse
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)


class CompressedImageField(models.BinaryField):
    """Custom field for storing compressed images as BLOB"""
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
    """Compress image using Pillow and return as bytes"""
    if not image_file:
        return None
    try:
        img = Image.open(image_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        return None


class Regione(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Categoria(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Auction(models.Model):
    """
    Auction model (asta a rialzo - ascending price auction)
    Replaces the Lottery model
    """
    STATUS_CHOICES = [
        ('draft', 'Bozza'),
        ('active', 'Attiva'),
        ('ending', 'In Chiusura'),
        ('closed', 'Chiusa'),
        ('completed', 'Completata'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    regione = models.ForeignKey(Regione, on_delete=models.PROTECT, default=1)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, default=1)
    item_value = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auctions_as_seller')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    kyc_completed = models.BooleanField(default=False)
    
    # Auction-specific fields
    starting_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    reserve_price = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True,
                                         help_text="Prezzo minimo per chiudere l'asta (opzionale)")
    bid_increment = models.DecimalField(max_digits=10, decimal_places=2, default=1.00,
                                        help_text="Incremento minimo per ogni rialzo")
    auction_end_time = models.DateTimeField(null=True, blank=True,
                                             help_text="Data e ora di chiusura dell'asta")
    
    # Compressed images stored as BLOB
    image_1 = CompressedImageField()
    image_2 = CompressedImageField()
    image_3 = CompressedImageField()
    
    image_1_description = models.CharField(max_length=255, blank=True)
    image_2_description = models.CharField(max_length=255, blank=True)
    image_3_description = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Current highest bid reference
    current_highest_bid = models.ForeignKey(
        'Bid', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    
    def __str__(self):
        return self.title
    
    def get_status_color(self):
        status_colors = {
            'draft': 'secondary', 'active': 'success',
            'ending': 'warning', 'closed': 'info', 'completed': 'dark'
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_status_display(self):
        status_display = {
            'draft': 'Bozza', 'active': 'Attiva',
            'ending': 'In Chiusura', 'closed': 'Chiusa', 'completed': 'Completata'
        }
        return status_display.get(self.status, self.status)

    def get_absolute_url(self):
        return reverse('lotteries:detail', kwargs={'lottery_id': self.id})

    @property
    def bids_count(self):
        return self.bids.count()

    @property
    def unique_bidders_count(self):
        return self.bids.values('bidder').distinct().count()

    @property
    def current_price(self):
        if self.current_highest_bid:
            return self.current_highest_bid.amount
        return self.starting_price

    @property
    def minimum_next_bid(self):
        if self.current_highest_bid:
            return self.current_highest_bid.amount + self.bid_increment
        return self.starting_price

    @property
    def is_expired(self):
        if not self.auction_end_time:
            return False
        return timezone.now() > self.auction_end_time

    @property
    def time_remaining(self):
        if not self.auction_end_time:
            return None
        if self.is_expired:
            return timedelta(0)
        return self.auction_end_time - timezone.now()

    @property
    def is_reserve_met(self):
        if not self.reserve_price:
            return True
        return self.current_price >= self.reserve_price

    @property
    def main_image_data_uri(self):
        if not self.image_1:
            return None
        encoded = base64.b64encode(self.image_1).decode('ascii')
        return f"data:image/jpeg;base64,{encoded}"

    @property
    def image_2_data_uri(self):
        if not self.image_2:
            return None
        encoded = base64.b64encode(self.image_2).decode('ascii')
        return f"data:image/jpeg;base64,{encoded}"

    @property
    def image_3_data_uri(self):
        if not self.image_3:
            return None
        encoded = base64.b64encode(self.image_3).decode('ascii')
        return f"data:image/jpeg;base64,{encoded}"

    def save(self, *args, **kwargs):
        if self.status == 'active' and not self.kyc_completed:
            if not getattr(self.seller, 'is_verified', False):
                raise ValidationError("Cannot activate auction without KYC verification")
            self.kyc_completed = True
        
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
        self._image_1_file = image_file
    
    def set_image_2(self, image_file):
        self._image_2_file = image_file
        
    def set_image_3(self, image_file):
        self._image_3_file = image_file

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='mercato_au_status_idx'),
            models.Index(fields=['seller', 'status'], name='mercato_au_seller_idx'),
            models.Index(fields=['auction_end_time'], name='mercato_au_endtime_idx'),
        ]


# Backwards compatibility alias
Lottery = Auction


class Bid(models.Model):
    """
    Bid model for auction system
    Replaces LotteryTicket
    """
    STATUS_CHOICES = [
        ('pending', 'In attesa'),
        ('payment_processing', 'Elaborazione pagamento'),
        ('payment_failed', 'Pagamento fallito'),
        ('completed', 'Completato'),
        ('outbid', 'Superato'),
        ('refunded', 'Rimborsato'),
        ('winning', 'Offerta Vincente'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    placed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_highest = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-placed_at']
        indexes = [
            models.Index(fields=['auction', '-placed_at'], name='mercato_bid_auction_idx'),
            models.Index(fields=['bidder', '-placed_at'], name='mercato_bid_bidder_idx'),
            models.Index(fields=['status'], name='mercato_bid_status_idx'),
        ]
    
    def __str__(self):
        return f"Bid #{self.id} - €{self.amount} on {self.auction.title}"
    
    def save(self, *args, **kwargs):
        highest = self.auction.bids.filter(is_highest=True).first()
        if not highest or self.amount > highest.amount:
            self.is_highest = True
            if highest:
                highest.is_highest = False
                highest.status = 'outbid'
                highest.save()
            self.auction.current_highest_bid = self
            self.auction.save()
        
        super().save(*args, **kwargs)


# Backwards compatibility alias
LotteryTicket = Bid


class AuctionResult(models.Model):
    """
    Auction result record - winner and final details
    Replaces WinnerDrawing
    """
    STATUS_CHOICES = [
        ('pending', 'In attesa'),
        ('completed', 'Completato'),
        ('cancelled', 'Annullato'),
        ('reserve_not_met', 'Riserva non raggiunta'),
    ]
    
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='results')
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_auctions')
    winning_bid = models.ForeignKey(Bid, on_delete=models.SET_NULL, null=True, blank=True)
    final_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    closed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    is_shipped = models.BooleanField(default=False, help_text="Se il premio è stato spedito al vincitore")
    shipped_at = models.DateTimeField(null=True, blank=True, help_text="Data e ora di spedizione del premio")
    
    class Meta:
        ordering = ['-closed_at']
        indexes = [
            models.Index(fields=['status', 'closed_at'], name='mercato_ar_status_idx'),
        ]
    
    def __str__(self):
        return f"Risultato Asta {self.auction.title} - {self.closed_at}"
    
    def mark_as_shipped(self):
        self.is_shipped = True
        self.shipped_at = timezone.now()
        self.save()
    
    def get_status_display(self):
        if self.is_shipped:
            return f"Spedito il {self.shipped_at.strftime('%d %b %Y alle %H:%M')}"
        return "In attesa di spedizione"


# Backwards compatibility alias
WinnerDrawing = AuctionResult


# Django signals
def auction_pre_save(sender, instance, **kwargs):
    if instance.status == 'active' and not instance.kyc_completed:
        if not getattr(instance.seller, 'is_verified', False):
            raise ValidationError("Cannot activate auction: seller KYC verification required")
        instance.kyc_completed = True


signals.pre_save.connect(auction_pre_save, sender=Auction)
