import base64
import logging
import uuid
from decimal import Decimal
from io import BytesIO

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
    regione = models.ForeignKey(Regione, on_delete=models.PROTECT, default=1)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, default=1)
    item_value = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    items_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lotteries_as_seller')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    kyc_completed = models.BooleanField(default=False)
    expiration_date = models.DateTimeField(null=True, blank=True)

    # Manual drawing configuration
    can_manually_draw = models.BooleanField(default=True)
    min_draw_delay_hours = models.PositiveIntegerField(default=24)
    
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

    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.items_count
    
    @property
    def is_expired(self):
        if not self.expiration_date:
            return False
        return timezone.now() > self.expiration_date

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
            models.Index(fields=['status', 'created_at'], name='mercato_lo_status_7a9a5f_idx'),
            models.Index(fields=['seller', 'status'], name='mercato_lo_seller_709b23_idx'),
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
    
    # Shipping tracking fields
    is_shipped = models.BooleanField(default=False, help_text="Se il premio è stato spedito al vincitore")
    shipped_at = models.DateTimeField(null=True, blank=True, help_text="Data e ora di spedizione del premio")
    
    class Meta:
        ordering = ['-drawn_at']
        indexes = [
            models.Index(fields=['status', 'drawn_at'], name='mercato_lo_status_e2b8f1_idx'),
        ]
    
    def __str__(self):
        return f"Estrazione {self.lottery.title} - {self.drawn_at}"
    
    def mark_as_shipped(self):
        """Marca il premio come spedito e registra la data/ora"""
        self.is_shipped = True
        self.shipped_at = timezone.now()
        self.save()
    
    def get_status_display(self):
        """Ritorna lo status di spedizione formattato"""
        if self.is_shipped:
            return f"Spedito il {self.shipped_at.strftime('%d %b %Y alle %H:%M')}"
        else:
            return "In attesa di spedizione"


# =====================================================================
# AUCTION SYSTEM MODELS
# =====================================================================

class Auction(models.Model):
    """
    Main auction model - replaces Lottery model for new auction system
    Supports ascending bids (aste a rialzo)
    """
    STATUS_CHOICES = [
        ('draft', 'Bozza'),
        ('active', 'Attiva'),
        ('paused', 'In Pausa'),
        ('closed', 'Chiusa'),
        ('completed', 'Completata'),
        ('cancelled', 'Annullata'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    regione = models.ForeignKey(Regione, on_delete=models.PROTECT, default=1)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, default=1)
    item_value = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    
    # Auction-specific fields
    starting_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    reserve_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)], null=True, blank=True)
    bid_increment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('10.00'), validators=[MinValueValidator(1.00)])
    auction_end_time = models.DateTimeField(null=True, blank=True)
    current_highest_bid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    current_highest_bidder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='winning_auctions')
    
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auctions_as_seller')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    kyc_completed = models.BooleanField(default=False)
    
    # Auto-close settings
    auto_close_on_end_time = models.BooleanField(default=True, help_text="Chiudi automaticamente l'asta quando scade il tempo")
    
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
    closed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def get_status_color(self):
        """Get bootstrap color class for status badge"""
        status_colors = {
            'draft': 'secondary',
            'active': 'success',
            'paused': 'warning',
            'closed': 'info',
            'completed': 'primary',
            'cancelled': 'danger'
        }
        return status_colors.get(self.status, 'secondary')
    
    def get_status_display(self):
        """Get display name for status"""
        status_display = {
            'draft': 'Bozza',
            'active': 'Attiva',
            'paused': 'In Pausa',
            'closed': 'Chiusa',
            'completed': 'Completata',
            'cancelled': 'Annullata'
        }
        return status_display.get(self.status, self.status)
    
    def get_absolute_url(self):
        return reverse('lotteries:auction_detail', kwargs={'auction_id': self.id})
    
    @property
    def bids_count(self):
        if hasattr(self, 'bids_count_annotation'):
            return self.bids_count_annotation
        return self.bids.filter(status='active').count()
    
    @property
    def total_bid_amount(self):
        """Total amount of all active bids"""
        return self.bids.filter(status='active').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def is_expired(self):
        if not self.auction_end_time:
            return False
        return timezone.now() > self.auction_end_time
    
    @property
    def time_remaining(self):
        """Time remaining until auction ends"""
        if not self.auction_end_time or self.status != 'active':
            return None
        remaining = self.auction_end_time - timezone.now()
        if remaining.total_seconds() <= 0:
            return None
        return remaining
    
    @property
    def minimum_next_bid(self):
        """Minimum amount for next bid"""
        return self.current_highest_bid + self.bid_increment
    
    @property
    def reserve_met(self):
        """Check if reserve price is met"""
        if not self.reserve_price:
            return True
        return self.current_highest_bid >= self.reserve_price
    
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
    
    def place_bid(self, bidder, amount):
        """
        Place a bid on this auction
        Returns the created Bid object
        Raises ValidationError if bid is invalid
        """
        # Check auction is active
        if self.status != 'active':
            raise ValidationError("L'asta non è attiva")
        
        # Check auction not expired
        if self.is_expired:
            raise ValidationError("L'asta è scaduta")
        
        # Check minimum bid amount
        if amount < self.minimum_next_bid:
            raise ValidationError(
                f"L'offerta deve essere di almeno {self.minimum_next_bid:.2f} EUR"
            )
        
        # Prevent self-bidding
        if bidder == self.seller:
            raise ValidationError("Non puoi offrire sulla tua asta")
        
        # Create the bid
        bid = Bid.objects.create(
            auction=self,
            bidder=bidder,
            amount=amount,
            status='active'
        )
        
        # Update auction's current highest bid
        self.current_highest_bid = amount
        self.current_highest_bidder = bidder
        self.save()
        
        return bid
    
    def close_auction(self):
        """
        Close the auction and determine winner
        Returns the AuctionResult object
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Lock the auction row
            auction = Auction.objects.select_for_update().get(id=self.id)
            
            # Check status
            if auction.status != 'active':
                raise ValidationError("L'asta non è attiva")
            
            # Get highest bid
            highest_bid = auction.bids.filter(status='active').order_by('-amount').first()
            
            # Create auction result
            result = AuctionResult.objects.create(
                auction=auction,
                winner=highest_bid.bidder if highest_bid else None,
                winning_bid=highest_bid,
                final_price=highest_bid.amount if highest_bid else Decimal('0.00'),
                status='completed' if highest_bid and auction.reserve_met else 'no_winner'
            )
            
            # Update auction status
            auction.status = 'completed' if highest_bid and auction.reserve_met else 'closed'
            auction.closed_at = timezone.now()
            auction.save()
            
            # Mark all other bids as outbid
            if highest_bid:
                auction.bids.filter(status='active').exclude(id=highest_bid.id).update(
                    status='outbid',
                    outbid_at=timezone.now()
                )
            
            return result
    
    def cancel_auction(self, reason=''):
        """
        Cancel the auction and refund all bids
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Lock the auction row
            auction = Auction.objects.select_for_update().get(id=self.id)
            
            if auction.status not in ['active', 'paused']:
                raise ValidationError("L'asta non può essere annullata")
            
            # Mark all bids as refunded
            auction.bids.filter(status='active').update(status='refunded')
            
            # Update auction status
            auction.status = 'cancelled'
            auction.closed_at = timezone.now()
            auction.save()
            
            # Create auction result
            AuctionResult.objects.create(
                auction=auction,
                winner=None,
                winning_bid=None,
                final_price=Decimal('0.00'),
                status='cancelled',
                cancellation_reason=reason
            )
    
    def save(self, *args, **kwargs):
        # Check KYC validation before activating auction
        if self.status == 'active' and not self.kyc_completed:
            # Check if seller is verified
            if not getattr(self.seller, 'is_verified', False):
                raise ValidationError("Cannot activate auction: seller KYC verification required")
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
            models.Index(fields=['auction_end_time']),
            models.Index(fields=['current_highest_bid']),
        ]


class Bid(models.Model):
    """
    Bid model - replaces LotteryTicket for auction system
    Represents a bid/shares on an auction
    """
    STATUS_CHOICES = [
        ('pending', 'In Attesa'),
        ('active', 'Attiva'),
        ('outbid', 'Superata'),
        ('winning', 'Vincente'),
        ('refunded', 'Rimborsata'),
        ('cancelled', 'Annullata'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auction_bids')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0.01)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    outbid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['auction', 'status']),
            models.Index(fields=['bidder', 'status']),
            models.Index(fields=['amount']),
        ]
        unique_together = ['auction', 'bidder', 'created_at']  # Prevent duplicate bids at same time
    
    def __str__(self):
        return f"Bid {self.id} - {self.auction.title} - {self.amount:.2f} EUR"
    
    def mark_as_outbid(self):
        """Mark this bid as outbid"""
        self.status = 'outbid'
        self.outbid_at = timezone.now()
        self.save()
    
    def mark_as_winning(self):
        """Mark this bid as the winning bid"""
        self.status = 'winning'
        self.save()
    
    def mark_as_refunded(self):
        """Mark this bid as refunded"""
        self.status = 'refunded'
        self.refunded_at = timezone.now()
        self.save()


class AuctionResult(models.Model):
    """
    Auction result model - replaces WinnerDrawing for auction system
    Records the outcome of an auction
    """
    STATUS_CHOICES = [
        ('completed', 'Completato'),
        ('no_winner', 'Nessun Vincitore'),
        ('cancelled', 'Annullato'),
    ]
    
    auction = models.OneToOneField(Auction, on_delete=models.CASCADE, related_name='result')
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_auctions')
    winning_bid = models.ForeignKey(Bid, on_delete=models.SET_NULL, null=True, blank=True)
    final_price = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    
    determined_at = models.DateTimeField(auto_now_add=True)
    
    # Additional result details
    total_bids = models.PositiveIntegerField(default=0)
    total_refunded_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    
    # Cancellation details
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # Shipping tracking fields (inherited from WinnerDrawing)
    is_shipped = models.BooleanField(default=False, help_text="Se il premio è stato spedito al vincitore")
    shipped_at = models.DateTimeField(null=True, blank=True, help_text="Data e ora di spedizione del premio")
    
    class Meta:
        ordering = ['-determined_at']
        indexes = [
            models.Index(fields=['status', 'determined_at']),
        ]
    
    def __str__(self):
        return f"Auction Result: {self.auction.title} - {self.final_price:.2f} EUR"
    
    def mark_as_shipped(self):
        """Mark the item as shipped"""
        self.is_shipped = True
        self.shipped_at = timezone.now()
        self.save()
    
    def get_status_display(self):
        """Get formatted status display"""
        status_display = {
            'completed': f'Completato - {self.final_price:.2f} EUR',
            'no_winner': 'Nessun Vincitore (prezzo di riserva non raggiunto)',
            'cancelled': f'Annullato - {self.cancellation_reason}' if self.cancellation_reason else 'Annullato'
        }
        return status_display.get(self.status, self.status)
    
    def get_shipping_status_display(self):
        """Get shipping status formatted"""
        if self.is_shipped:
            return f"Spedito il {self.shipped_at.strftime('%d %b %Y alle %H:%M')}"
        else:
            return "In attesa di spedizione"


# =====================================================================
# LEGACY MODELS (kept for backwards compatibility)
# =====================================================================

# Django signals
def lottery_pre_save(sender, instance, **kwargs):
    """Check KYC validation and calculate ticket price"""
    if instance.status == 'active' and not instance.kyc_completed:
        # Check if seller is verified (is_verified field from CustomUser)
        if not getattr(instance.seller, 'is_verified', False):
            raise ValidationError("Cannot activate lottery: seller KYC verification required")
        instance.kyc_completed = True


def handle_lottery_fulfillment(sender, instance, created, **kwargs):
    """No-op: lotteries are closed/drawn manually."""
    return


# Connect signals
signals.pre_save.connect(lottery_pre_save, sender=Lottery)
signals.post_save.connect(handle_lottery_fulfillment, sender=Lottery)