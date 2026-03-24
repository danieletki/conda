from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import timedelta
from .models import Lottery, WinnerDrawing, Auction, Bid, AuctionResult
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


@shared_task
def perform_manual_draw(lottery_id, initiated_by_user_id):
    """
    Esegue l'estrazione manuale del vincitore per una lotteria specifica.
    Chiamato dal venditore dalla view initiate_draw().
    """
    try:
        logger.info(f"[DRAW] Starting manual draw for lottery {lottery_id} by user {initiated_by_user_id}")
        
        with transaction.atomic():
            # Lock the lottery row to prevent concurrent extractions
            lottery = Lottery.objects.select_for_update().get(id=lottery_id)
            logger.info(f"[DRAW] Lottery found: {lottery.title}")

            # Validare che lottery.seller.id == initiated_by_user_id (solo il venditore può estrarre)
            if lottery.seller.id != initiated_by_user_id:
                logger.error(f"Unauthorized: User {initiated_by_user_id} tried to draw lottery {lottery_id}")
                return

            # Check if drawing already exists
            if WinnerDrawing.objects.filter(lottery=lottery).exists():
                logger.warning(f"[DRAW] Drawing already exists for lottery {lottery.id}")
                return

            logger.info(f"[DRAW] Processing manual extraction for lottery {lottery.title} ({lottery.id}) by user {initiated_by_user_id}")

            # Get all paid tickets
            paid_tickets = lottery.tickets.filter(payment_status='completed')
            logger.info(f"[DRAW] Paid tickets found: {paid_tickets.count()}")

            if not paid_tickets.exists():
                logger.warning(f"[DRAW] No paid tickets for lottery {lottery.id}. Cannot extract winner.")
                return

            # Selezionare casualmente uno tra i biglietti pagati
            winning_ticket = random.choice(list(paid_tickets))
            winner = winning_ticket.buyer
            logger.info(f"[DRAW] Winner extracted: {winner.email}, Ticket: {winning_ticket.ticket_number}")

            # Creare record WinnerDrawing
            drawing = WinnerDrawing.objects.create(
                lottery=lottery,
                winner=winner,
                winning_ticket=winning_ticket,
                status='completed',
                prize_amount=lottery.item_value
            )
            logger.info(f"[DRAW] WinnerDrawing created: {drawing.id}")

            # Aggiornare lotteria: lottery.status = 'drawn' e salvare
            lottery.status = 'drawn'
            lottery.save()
            logger.info(f"[DRAW] Lottery status updated to 'drawn'")

            logger.info(f"[DRAW] Manual winner extracted for lottery {lottery.id}: {winner.email}")

            # Inviare email
            try:
                send_lottery_won_email(winning_ticket, winner, drawing)
                send_seller_winner_notification_email(lottery, winner, winning_ticket, drawing)
                logger.info(f"[DRAW] Emails sent to {winner.email} and seller")
            except Exception as e:
                logger.error(f"[DRAW] Error sending emails for manual draw of lottery {lottery.id}: {e}")

            logger.info(f"[DRAW] Manual draw completed successfully for lottery {lottery.id}")

    except Lottery.DoesNotExist:
        logger.error(f"[DRAW] Lottery {lottery_id} not found")
    except Exception as e:
        logger.error(f"[DRAW] Error performing manual draw for lottery {lottery_id}: {e}", exc_info=True)
        raise


# =====================================================================
# AUCTION TASKS
# =====================================================================

@shared_task
def close_expired_auctions():
    """
    Close all expired auctions that have auto_close_on_end_time enabled
    Runs periodically via Celery Beat
    """
    logger.info("[AUCTION] Starting close_expired_auctions task")
    
    try:
        expired_auctions = Auction.objects.filter(
            status='active',
            auction_end_time__lte=timezone.now(),
            auto_close_on_end_time=True
        )
        
        closed_count = 0
        for auction in expired_auctions:
            try:
                result = auction.close_auction()
                closed_count += 1
                logger.info(f"[AUCTION] Closed expired auction {auction.id}: {auction.title}")
                
                # TODO: Send notification emails to winner and seller
                # send_auction_won_email(result)
                # send_seller_auction_closed_email(result)
                
            except Exception as e:
                logger.error(f"[AUCTION] Error closing auction {auction.id}: {e}")
        
        logger.info(f"[AUCTION] Closed {closed_count} expired auctions")
        return closed_count
        
    except Exception as e:
        logger.error(f"[AUCTION] Error in close_expired_auctions: {e}", exc_info=True)
        raise


@shared_task
def refund_outbid_bids(auction_id, winning_bid_id):
    """
    Refund all outbid bids for an auction except the winning bid
    Called after auction closes
    """
    logger.info(f"[AUCTION] Starting refund_outbid_bids for auction {auction_id}")
    
    try:
        with transaction.atomic():
            auction = Auction.objects.select_for_update().get(id=auction_id)
            
            # Mark all active bids except winning bid as outbid
            outbid_bids = auction.bids.filter(status='active').exclude(id=winning_bid_id)
            refunded_count = 0
            
            for bid in outbid_bids:
                bid.mark_as_outbid()
                # TODO: Process actual refund through payment system
                # refund_payment_transaction(bid.payment_transaction)
                refunded_count += 1
                logger.info(f"[AUCTION] Marked bid {bid.id} as outbid for auction {auction_id}")
            
            logger.info(f"[AUCTION] Refunded {refunded_count} outbid bids for auction {auction_id}")
            return refunded_count
            
    except Auction.DoesNotExist:
        logger.error(f"[AUCTION] Auction {auction_id} not found")
    except Exception as e:
        logger.error(f"[AUCTION] Error in refund_outbid_bids for auction {auction_id}: {e}", exc_info=True)
        raise


@shared_task
def send_outbid_notifications(auction_id, outbid_bidder_id, outbid_amount, new_bid_amount):
    """
    Send email notification to bidder who was outbid
    Called when a new higher bid is placed
    """
    logger.info(f"[AUCTION] Sending outbid notification to bidder {outbid_bidder_id} for auction {auction_id}")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        auction = Auction.objects.get(id=auction_id)
        outbid_user = User.objects.get(id=outbid_bidder_id)
        
        # TODO: Implement email notification
        # send_outbid_email(outbid_user, auction, outbid_amount, new_bid_amount)
        
        logger.info(f"[AUCTION] Outbid notification sent to {outbid_user.email}")
        
    except Auction.DoesNotExist:
        logger.error(f"[AUCTION] Auction {auction_id} not found")
    except Exception as e:
        logger.error(f"[AUCTION] Error sending outbid notification: {e}", exc_info=True)
