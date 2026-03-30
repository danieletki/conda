from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Auction, Bid, AuctionResult
import logging

logger = logging.getLogger(__name__)


@shared_task
def close_auction(auction_id):
    """Close an auction and determine the winner based on highest bid."""
    try:
        with transaction.atomic():
            auction = Auction.objects.select_for_update().get(id=auction_id)
            
            if auction.status in ['closed', 'completed']:
                logger.warning(f"Auction {auction.id} is already closed")
                return
            
            logger.info(f"Closing auction {auction.title} ({auction.id})")
            
            highest_bid = auction.bids.filter(status='completed').order_by('-amount').first()
            
            if highest_bid:
                if auction.reserve_price and highest_bid.amount < auction.reserve_price:
                    AuctionResult.objects.create(
                        auction=auction, winner=None, winning_bid=highest_bid,
                        final_price=highest_bid.amount, status='reserve_not_met'
                    )
                    logger.info(f"Auction {auction.id} closed but reserve not met")
                else:
                    result = AuctionResult.objects.create(
                        auction=auction, winner=highest_bid.bidder, winning_bid=highest_bid,
                        final_price=highest_bid.amount, status='completed'
                    )
                    logger.info(f"Auction {auction.id} closed with winner: {highest_bid.bidder.email}")
                    highest_bid.status = 'winning'
                    highest_bid.save()
            else:
                AuctionResult.objects.create(
                    auction=auction, winner=None, winning_bid=None,
                    final_price=0, status='completed'
                )
                logger.info(f"Auction {auction.id} closed with no bids")
            
            auction.status = 'closed'
            auction.save()
            
    except Auction.DoesNotExist:
        logger.error(f"Auction {auction_id} not found")
    except Exception as e:
        logger.error(f"Error closing auction {auction_id}: {e}", exc_info=True)
        raise


@shared_task
def close_expired_auctions():
    """Close auctions that have reached their end time."""
    now = timezone.now()
    expired_auctions = Auction.objects.filter(status='active', auction_end_time__lte=now)
    
    count = 0
    for auction in expired_auctions:
        try:
            close_auction.delay(auction.id)
            count += 1
        except Exception as e:
            logger.error(f"Error triggering close for auction {auction.id}: {e}")
    
    if count > 0:
        logger.info(f"Triggered close for {count} expired auctions")
    return count


@shared_task
def notify_auction_ending_soon():
    """Notify users when auctions are ending soon."""
    now = timezone.now()
    soon_threshold = now + timedelta(hours=1)
    
    ending_auctions = Auction.objects.filter(
        status='active', auction_end_time__gt=now, auction_end_time__lte=soon_threshold
    )
    
    for auction in ending_auctions:
        bidders = auction.bids.values_list('bidder', flat=True).distinct()
        for bidder_id in bidders:
            logger.info(f"Would notify bidder {bidder_id} that auction {auction.id} ends soon")


@shared_task
def update_auction_statuses():
    """Update auction statuses based on time remaining."""
    now = timezone.now()
    ending_threshold = now + timedelta(hours=1)
    
    auctions_to_end = Auction.objects.filter(
        status='active', auction_end_time__gt=now, auction_end_time__lte=ending_threshold
    )
    
    count = 0
    for auction in auctions_to_end:
        auction.status = 'ending'
        auction.save()
        count += 1
    
    if count > 0:
        logger.info(f"Updated {count} auctions to 'ending' status")
    return count


@shared_task
def perform_manual_draw(lottery_id, initiated_by_user_id):
    """DEPRECATED: Use close_auction."""
    logger.warning(f"perform_manual_draw is deprecated for auction {lottery_id}")
    close_auction.delay(lottery_id)


@shared_task
def process_lottery_extraction(lottery_id):
    """DEPRECATED: Use close_auction."""
    logger.warning(f"process_lottery_extraction is deprecated for auction {lottery_id}")
    close_auction.delay(lottery_id)
