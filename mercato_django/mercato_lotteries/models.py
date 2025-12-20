from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

User = get_user_model()


class Category(models.Model):
    """
    Category model for organizing lotteries
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Lottery(models.Model):
    """
    Main lottery model
    """
    STATUS_CHOICES = [
        ('draft', 'Bozza'),
        ('active', 'Attiva'),
        ('ended', 'Terminata'),
        ('cancelled', 'Cancellata'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='lottery_images/', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='lotteries')
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    max_tickets = models.PositiveIntegerField()
    max_tickets_per_user = models.PositiveIntegerField(default=10)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    draw_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_lotteries')
    is_featured = models.BooleanField(default=False)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def tickets_sold(self):
        return self.tickets.count()

    @property
    def tickets_remaining(self):
        return self.max_tickets - self.tickets_sold

    @property
    def is_active(self):
        now = timezone.now()
        return self.status == 'active' and self.start_date <= now <= self.end_date

    @property
    def revenue(self):
        return Decimal(str(self.tickets_sold)) * self.ticket_price

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'end_date']),
            models.Index(fields=['category', 'status']),
        ]


class LotteryTicket(models.Model):
    """
    Individual lottery tickets
    """
    STATUS_CHOICES = [
        ('active', 'Attivo'),
        ('winning', 'Vincente'),
        ('losing', 'Perdente'),
        ('refunded', 'Rimborsato'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lottery_tickets')
    purchase_date = models.DateTimeField(auto_now_add=True)
    ticket_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_winning = models.BooleanField(default=False)
    prize_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"{self.lottery.id}-{self.user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ['lottery', 'user']
        ordering = ['-purchase_date']


class LotteryResult(models.Model):
    """
    Results for completed lotteries
    """
    lottery = models.OneToOneField(Lottery, on_delete=models.CASCADE, related_name='result')
    draw_date = models.DateTimeField()
    winning_ticket = models.ForeignKey(LotteryTicket, on_delete=models.CASCADE, related_name='winning_result')
    winner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='won_results')
    total_prize = models.DecimalField(max_digits=15, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Result for {self.lottery.title}"

    class Meta:
        ordering = ['-draw_date']


class LotteryComment(models.Model):
    """
    User comments on lotteries
    """
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lottery_comments')
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.lottery.title}"

    class Meta:
        ordering = ['-created_at']
