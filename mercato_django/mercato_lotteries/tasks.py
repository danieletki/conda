from celery import shared_task
from django.db import transaction
from .models import Lottery, WinnerDrawing
from mercato_notifications.email_service import send_lottery_won_email, send_seller_winner_notification_email
import random
import logging

logger = logging.getLogger(__name__)

# NOTE: Automatic winner extraction has been removed as of [date]
# The system now uses manual extraction only. Sellers must manually trigger
# the extraction process when they decide to close a lottery.
# This change supports the new per-lottery manual draw workflow.

@shared_task
def process_lottery_extraction(lottery_id):
    """
    Process winner extraction for a single lottery
    """
    try:
        with transaction.atomic():
            # Lock the lottery row to prevent concurrent extractions
            lottery = Lottery.objects.select_for_update().get(id=lottery_id)
            
            # Double check status and existence of drawing to prevent race conditions
            if WinnerDrawing.objects.filter(lottery=lottery).exists():
                logger.warning(f"Drawing already exists for lottery {lottery.id}")
                return
            
            logger.info(f"Processing extraction for lottery {lottery.title} ({lottery.id})")
            
            # Get all paid tickets
            paid_tickets = lottery.tickets.filter(payment_status='completed')
            
            if not paid_tickets.exists():
                logger.warning(f"No paid tickets for lottery {lottery.id}. Cannot extract winner.")
                # Update status to completed but without winner or handle differently?
                # For now just log and return.
                return

            # Randomly select a winner
            winning_ticket = random.choice(list(paid_tickets))
            winner = winning_ticket.buyer
            
            # Create WinnerDrawing record
            drawing = WinnerDrawing.objects.create(
                lottery=lottery,
                winner=winner,
                winning_ticket=winning_ticket,
                status='completed',
                prize_amount=lottery.item_value
            )
            
            # Update lottery status
            lottery.status = 'drawn'
            lottery.save()
            
            logger.info(f"Winner extracted for lottery {lottery.id}: {winner.email}")
            
            # Send emails
            # We send emails after transaction commit ideally, but inside is also ok for now.
            # If email fails, we still want the drawing to persist.
            # So we catch exceptions for email.
            try:
                send_lottery_won_email(winning_ticket, winner, drawing)
                send_seller_winner_notification_email(lottery, winner, winning_ticket, drawing)
            except Exception as e:
                logger.error(f"Error sending emails for lottery {lottery.id}: {e}")

    except Lottery.DoesNotExist:
        logger.error(f"Lottery {lottery_id} not found")
    except Exception as e:
        logger.error(f"Error extracting winner for lottery {lottery_id}: {e}")
        raise
