from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Notification, EmailNotification, NotificationSettings
from .email_service import (
    send_registration_email,
    send_kyc_approved_email,
    send_kyc_rejected_email,
    send_lottery_activated_email,
    send_ticket_purchased_email,
    send_lottery_won_email,
    send_seller_winner_notification_email,
    send_lottery_lost_email,
    send_expiration_reminder_email
)
from mercato_lotteries.models import Lottery, LotteryTicket, WinnerDrawing
from mercato_accounts.models import CustomUser

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def user_created_or_updated(sender, instance, created, **kwargs):
    """
    Handle user registration and updates
    """
    if created:
        # Send registration email
        logger.info(f"Sending registration email to new user: {instance.email}")
        send_registration_email(instance)
        
        # Create notification settings
        NotificationSettings.objects.get_or_create(user=instance)


@receiver(post_save, sender=Lottery)
def lottery_status_changed(sender, instance, created, **kwargs):
    """
    Handle lottery status changes
    """
    if not created and instance.status == 'active':
        # Check if KYC is completed (this should already be done in the model's save method)
        if instance.kyc_completed:
            logger.info(f"Sending activation email for lottery: {instance.title}")
            send_lottery_activated_email(instance)


@receiver(post_save, sender=LotteryTicket)
def ticket_purchased(sender, instance, created, **kwargs):
    """
    Handle ticket purchase
    """
    if created and instance.payment_status == 'completed':
        logger.info(f"Sending ticket purchase confirmation to: {instance.buyer.email}")
        send_ticket_purchased_email(instance)


@receiver(post_save, sender=WinnerDrawing)
def lottery_drawn(sender, instance, created, **kwargs):
    """
    Handle lottery drawing completion
    """
    if created and instance.status == 'completed' and instance.winner:
        logger.info(f"Lottery drawn: {instance.lottery.title}, winner: {instance.winner.email}")
        
        # Send email to winner
        logger.info(f"Sending win notification to winner: {instance.winner.email}")
        send_lottery_won_email(instance.winning_ticket, instance.winner, instance)
        
        # Send email to seller with winner details
        logger.info(f"Sending winner notification to seller: {instance.lottery.seller.email}")
        send_seller_winner_notification_email(
            instance.lottery, 
            instance.winner, 
            instance.winning_ticket, 
            instance
        )
        
        # Send email to all other participants (optional - only if user settings allow it)
        send_lottery_results_to_participants(instance.lottery, instance)


def send_lottery_results_to_participants(lottery, drawing):
    """
    Send lottery results to all participants (non-winners)
    """
    participants = lottery.tickets.filter(
        payment_status='completed'
    ).exclude(
        buyer=drawing.winner
    ).select_related('buyer').distinct('buyer')
    
    for ticket in participants:
        # Check if user wants lottery result emails
        try:
            settings = NotificationSettings.objects.get(user=ticket.buyer)
            if settings.email_lottery_results:
                logger.info(f"Sending lottery result email to: {ticket.buyer.email}")
                send_lottery_lost_email(ticket, drawing.winner, drawing)
        except NotificationSettings.DoesNotExist:
            # If no settings found, send email anyway (default is True)
            logger.info(f"Sending lottery result email to: {ticket.buyer.email}")
            send_lottery_lost_email(ticket, drawing.winner, drawing)


def send_expiration_reminders():
    """
    Send expiration reminders for lotteries ending soon
    Run this as a scheduled task
    """
    from django.core.management.base import BaseCommand
    
    # Get lotteries expiring in 24 hours
    tomorrow = timezone.now() + timedelta(hours=24)
    expiring_soon = Lottery.objects.filter(
        status='active',
        expiration_date__lte=tomorrow,
        expiration_date__gte=timezone.now()
    )
    
    # Get lotteries expiring today
    today_end = timezone.now().replace(hour=23, minute=59, second=59)
    expiring_today = Lottery.objects.filter(
        status='active',
        expiration_date__lte=today_end,
        expiration_date__gte=timezone.now()
    )
    
    for lottery in expiring_soon:
        # Send reminders to users who visited the lottery or similar ones
        # This is a simplified version - in reality you'd track user interests
        interested_users = User.objects.filter(
            email__isnull=False
        ).exclude(
            email=''  # Skip users without email
        )[:50]  # Limit to 50 users to avoid spam
        
        time_remaining = lottery.expiration_date - timezone.now()
        hours_remaining = int(time_remaining.total_seconds() // 3600)
        
        for user in interested_users:
            try:
                # Check user notification settings
                settings = NotificationSettings.objects.get(user=user)
                if not settings.email_enabled:
                    continue
                    
                send_expiration_reminder_email(
                    user=user,
                    lottery=lottery,
                    time_remaining=f"{hours_remaining} ore",
                    notification_type='lottery_ending_soon'
                )
            except NotificationSettings.DoesNotExist:
                # Send anyway if no settings found
                send_expiration_reminder_email(
                    user=user,
                    lottery=lottery,
                    time_remaining=f"{hours_remaining} ore",
                    notification_type='lottery_ending_soon'
                )
    
    for lottery in expiring_today:
        # Send urgent reminders for lotteries expiring today
        interested_users = User.objects.filter(
            email__isnull=False
        ).exclude(
            email=''
        )[:20]  # Smaller limit for urgent emails
        
        for user in interested_users:
            try:
                settings = NotificationSettings.objects.get(user=user)
                if not settings.email_enabled:
                    continue
                    
                send_expiration_reminder_email(
                    user=user,
                    lottery=lottery,
                    time_remaining="poche ore",
                    notification_type='lottery_expiring_today'
                )
            except NotificationSettings.DoesNotExist:
                send_expiration_reminder_email(
                    user=user,
                    lottery=lottery,
                    time_remaining="poche ore",
                    notification_type='lottery_expiring_today'
                )


# Custom signal for KYC status changes
from django.dispatch import Signal

# Define custom signals
kyc_approved = Signal()
kyc_rejected = Signal()


@receiver(kyc_approved)
def handle_kyc_approved(sender, user, **kwargs):
    """Handle KYC approval"""
    logger.info(f"KYC approved for user: {user.email}")
    send_kyc_approved_email(user)


@receiver(kyc_rejected)
def handle_kyc_rejected(sender, user, kyc_ticket_id=None, **kwargs):
    """Handle KYC rejection"""
    logger.info(f"KYC rejected for user: {user.email}")
    send_kyc_rejected_email(user, kyc_ticket_id)


# Management command to run expiration reminders
class Command(BaseCommand):
    help = 'Send expiration reminder emails'
    
    def handle(self, *args, **options):
        self.stdout.write('Sending expiration reminders...')
        send_expiration_reminders()
        self.stdout.write(self.style.SUCCESS('Expiration reminders sent successfully!'))