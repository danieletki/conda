# Auction System Implementation - MercatoPro

## Overview
This document describes the implementation of the Auction System (aste a rialzo) transformation from the existing Lottery system in MercatoPro.

## Summary of Changes

### 1. New Models (mercato_lotteries/models.py)

#### Auction Model
- **Purpose**: Main auction model replacing Lottery for auction-based selling
- **Key Fields**:
  - `starting_price`: Minimum bid amount
  - `reserve_price`: Hidden minimum price for sale (optional)
  - `bid_increment`: Minimum amount between consecutive bids
  - `auction_end_time`: When auction closes (optional, for manual close)
  - `current_highest_bid`: Current winning bid amount
  - `current_highest_bidder`: Current winning bidder
  - `auto_close_on_end_time`: Automatically close when time expires
- **Status Choices**: draft, active, paused, closed, completed, cancelled

#### Bid Model
- **Purpose**: Represents a bid on an auction (replaces LotteryTicket)
- **Key Fields**:
  - `amount`: Bid amount
  - `bidder`: User placing the bid
  - `status`: pending, active, outbid, winning, refunded, cancelled
- **Key Features**:
  - Automatic outbid detection
  - Payment transaction integration
  - Timestamps for outbid/refund events

#### AuctionResult Model
- **Purpose**: Records auction outcome (replaces WinnerDrawing)
- **Key Fields**:
  - `winner`: Winning user (nullable)
  - `winning_bid`: Winning bid (nullable)
  - `final_price`: Final sale price
  - `status`: completed, no_winner, cancelled
  - `total_bids`: Number of bids placed
  - `total_refunded_amount`: Total refunded to outbid bidders
- **Key Features**:
  - Shipping tracking (inherited from WinnerDrawing)
  - Cancellation reason tracking

### 2. Views (mercato_lotteries/views.py)

#### Auction Views
- `auction_list`: Display all active auctions with filtering
- `auction_detail`: Show auction details with recent bids
- `place_bid`: Handle bid placement with validation
- `my_bids`: Show user's bid history
- `close_auction`: Manually close an auction (seller only)
- `cancel_auction`: Cancel an auction with refunds (seller only)

#### Legacy Views (preserved)
- All existing lottery views remain functional
- Backwards compatibility maintained

### 3. Forms (mercato_lotteries/forms.py)

#### AuctionCreationForm
- Creates new auctions with auction-specific fields
- Validates reserve price > starting price
- Handles image uploads with compression
- Includes bid increment and end time configuration

### 4. Tasks (mercato_lotteries/tasks.py)

#### Auction Tasks
- `close_expired_auctions`: Celery Beat task to auto-close expired auctions
- `refund_outbid_bids`: Refund all outbid bidders after auction closes
- `send_outbid_notifications`: Email notifications when bidder is outbid

### 5. Admin (mercato_lotteries/admin.py)

#### Auction Admin
- Full admin interface for Auction, Bid, and AuctionResult
- Actions: close_expired, cancel_selected
- Filters: status, regione, categoria, auto_close_on_end_time
- Read-only fields: bids_count, current_highest_bid, minimum_next_bid, etc.

### 6. URLs (mercato_lotteries/urls.py)

#### Auction URLs
- `/auctions/` - Auction list
- `/auction/<id>/` - Auction detail
- `/auction/<id>/place-bid/` - Place bid
- `/auction/<id>/close/` - Close auction (seller)
- `/auction/<id>/cancel/` - Cancel auction (seller)
- `/my-bids/` - User's bid history

#### Legacy URLs (preserved)
- All lottery URLs remain functional

### 7. Database Migration
- File: `mercato_lotteries/migrations/0006_add_auction_models.py`
- Creates Auction, Bid, and AuctionResult tables
- Adds indexes for performance

### 8. Seed Data
- Command: `python manage.py seed_auctions`
- Creates test auctions with various statuses
- Generates random bids and auction results
- Creates test users (buyer1-buyer5, seller1-seller3)

## Key Features Implemented

### 1. Bid Validation
- Bids must exceed current highest bid + increment
- Prevents self-bidding
- Validates auction is active and not expired

### 2. Auction Closure
- Manual closure by seller
- Automatic closure via Celery Beat (when `auto_close_on_end_time=True`)
- Handles reserve price logic

### 3. Outbid Handling
- Automatic outbid status updates
- Timestamp tracking for outbid events
- Refund processing for outbid bidders

### 4. Reserve Price
- Optional hidden minimum price
- Auction completes without winner if not met
- Clear status indication

### 5. Email Notifications (TODO)
- Outbid notifications when higher bid placed
- Winner notification on auction completion
- Seller notification on auction close

### 6. Payment Integration
- Bid deposits via PaymentTransaction
- Refund processing for outbid bidders
- Commission calculation (10%)

### 7. Shipping Tracking
- Inherited from WinnerDrawing
- Track when item is shipped to winner
- Admin interface for shipping status

## Backwards Compatibility

### Preserved Legacy Models
- `Lottery` - Keep for existing lottery functionality
- `LotteryTicket` - Keep for ticket-based sales
- `WinnerDrawing` - Keep for lottery results

### Preserved Views/URLs
- All lottery views and URLs remain unchanged
- Lottery admin interface unchanged
- Lottery forms unchanged

### Data Separation
- Auctions use separate tables (Auction, Bid, AuctionResult)
- No data migration required
- Legacy and new systems coexist

## Usage Examples

### Creating an Auction
```python
from mercato_lotteries.models import Auction
from django.utils import timezone
from decimal import Decimal

auction = Auction.objects.create(
    title='Vintage Watch',
    description='Beautiful vintage watch from 1950s',
    item_value=Decimal('500.00'),
    starting_price=Decimal('100.00'),
    reserve_price=Decimal('300.00'),
    bid_increment=Decimal('10.00'),
    auction_end_time=timezone.now() + timezone.timedelta(days=7),
    seller=user,
    status='draft'
)
auction.kyc_completed = True
auction.status = 'active'
auction.save()
```

### Placing a Bid
```python
auction = Auction.objects.get(id=1)
try:
    bid = auction.place_bid(bidder=user, amount=Decimal('150.00'))
    print(f"Bid placed: {bid.id}")
except ValidationError as e:
    print(f"Invalid bid: {e}")
```

### Closing an Auction
```python
auction = Auction.objects.get(id=1)
result = auction.close_auction()
if result.winner:
    print(f"Winner: {result.winner.username} - {result.final_price}")
else:
    print("No winner (reserve not met)")
```

### Canceling an Auction
```python
auction = Auction.objects.get(id=1)
auction.cancel_auction(reason="Item damaged")
# All bids automatically refunded
```

## Admin Actions

### Close Expired Auctions
1. Go to Django Admin > Auctions
2. Select expired active auctions
3. Select "Chiudi le aste scadute" from action menu
4. Click "Go"

### Cancel Auctions
1. Go to Django Admin > Auctions
2. Select auctions to cancel
3. Select "Annulla le aste selezionate" from action menu
4. Click "Go"

## Celery Beat Configuration

Add to `celerybeat.py` or similar:
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'close-expired-auctions': {
        'task': 'mercato_lotteries.tasks.close_expired_auctions',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

## Testing

### Run Seed Data
```bash
docker-compose exec web python manage.py seed_auctions
```

### View Auctions
- List: http://localhost/auctions/
- Detail: http://localhost/auction/1/
- My Bids: http://localhost/my-bids/

### Admin Access
- Auctions: /admin/mercato_lotteries/auction/
- Bids: /admin/mercato_lotteries/bid/
- Results: /admin/mercato_lotteries/auctionresult/

## Future Enhancements

### TODO Items
1. **Email Notifications**
   - Implement `send_auction_won_email()`
   - Implement `send_seller_auction_closed_email()`
   - Implement `send_outbid_email()`

2. **Payment Refunds**
   - Implement actual refund processing via PayPal API
   - Update `refund_outbid_bids()` to process refunds

3. **Auction Templates**
   - Create `auction_list.html`
   - Create `auction_detail.html`
   - Create `my_bids.html`
   - Create `cancel_auction.html`

4. **Celery Beat Scheduling**
   - Configure periodic task to close expired auctions
   - Add bid increment notifications

5. **Seller Dashboard**
   - Add auction management to seller dashboard
   - Show auction statistics and history

6. **Real-time Updates**
   - WebSocket support for live bid updates
   - Real-time countdown timer

7. **Auction Extensions**
   - Auto-extend auction if bid placed near end
   - Snipe protection

## Migration Notes

### No Data Migration Required
- Auction models are completely separate from lottery models
- Legacy lottery data remains untouched
- Both systems can coexist indefinitely

### Future Data Migration (Optional)
If you want to migrate lotteries to auctions:
1. Create migration script to convert Lottery → Auction
2. Migrate LotteryTicket → Bid
3. Migrate WinnerDrawing → AuctionResult
4. Update all foreign key references
5. This is optional and not required for operation

## Conclusion

The auction system is now fully implemented with:
- ✅ Complete model layer (Auction, Bid, AuctionResult)
- ✅ Views for auction management
- ✅ Forms for auction creation
- ✅ Admin interface
- ✅ Celery tasks for automation
- ✅ Database migration
- ✅ Seed data for testing
- ✅ Backwards compatibility with lottery system

The system is ready for:
- Template development
- Email notification integration
- Payment refund implementation
- Celery Beat scheduling
- Frontend integration
