from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mercato_lotteries.models import Auction, Bid, AuctionResult
from mercato_payments.models import PaymentTransaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
from io import BytesIO
from PIL import Image

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates database with seed auction data for testing'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding auction data...')
        
        self.stdout.write('Creating payment methods...')
        self.create_payment_methods()
        
        self.stdout.write('Creating buyers...')
        buyers = self.create_buyers()
        
        self.stdout.write('Creating sellers...')
        sellers = self.create_sellers()
        
        self.stdout.write('Creating auctions...')
        auctions = self.create_auctions(sellers)
        
        self.stdout.write('Creating auction bids...')
        self.create_auction_bids(auctions, buyers)
        
        self.stdout.write(self.style.SUCCESS('✅ Auction seed data created successfully!'))

    def create_dummy_image(self):
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img = Image.new('RGB', (400, 300), color=color)
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer

    def create_payment_methods(self):
        from mercato_payments.models import PaymentMethod
        methods = [
            ('PayPal', 'paypal', 3.50),
            ('Credit Card', 'credit_card', 2.00),
        ]
        for name, type, fee in methods:
            PaymentMethod.objects.get_or_create(
                method_type=type,
                defaults={'name': name, 'processing_fee': fee}
            )
        self.stdout.write(f'  Created/Checked payment methods')

    def create_buyers(self):
        buyers = []
        for i in range(1, 6):
            username = f'buyer{i}'
            email = f'buyer{i}@example.com'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_verified': True
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            buyers.append(user)
        self.stdout.write(f'  Created {len(buyers)} buyers')
        return buyers

    def create_sellers(self):
        sellers = []
        for i in range(1, 4):
            username = f'seller{i}'
            email = f'seller{i}@example.com'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_verified': True
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            sellers.append(user)
        self.stdout.write(f'  Created {len(sellers)} sellers')
        return sellers

    def create_auctions(self, sellers):
        auctions = []
        statuses = ['draft', 'active', 'active', 'active', 'completed', 'active', 'draft', 'cancelled', 'active', 'active']
        
        for i, status in enumerate(statuses):
            seller = random.choice(sellers)
            title = f'Auction Item {i+1}'
            item_value = Decimal(random.randint(100, 1000))
            starting_price = Decimal(random.randint(50, int(item_value * 0.7)))
            reserve_price = Decimal(random.randint(int(starting_price * 1.1), int(item_value * 0.9))) if random.random() > 0.3 else None
            
            # Set auction end time
            auction_end_time = None
            if status == 'active':
                # Active auctions end in future
                auction_end_time = timezone.now() + timedelta(days=random.randint(1, 7))
            elif status in ['completed', 'cancelled']:
                # Completed/cancelled auctions ended in past
                auction_end_time = timezone.now() - timedelta(days=random.randint(1, 30))
            
            auction, created = Auction.objects.get_or_create(
                title=title,
                defaults={
                    'description': f'This is a description for {title}. Up for auction!',
                    'item_value': item_value,
                    'starting_price': starting_price,
                    'reserve_price': reserve_price,
                    'bid_increment': Decimal('10.00'),
                    'auction_end_time': auction_end_time,
                    'seller': seller,
                    'status': 'draft',  # Create as draft first
                }
            )
            
            # Add images if just created
            if created:
                auction.set_image_1(self.create_dummy_image())
                auction.image_1_description = "Front view"
                auction.set_image_2(self.create_dummy_image())
                auction.image_2_description = "Side view"
                auction.set_image_3(self.create_dummy_image())
                auction.image_3_description = "Detail view"
                
                # Fix kyc if active
                if status == 'active':
                    auction.kyc_completed = True
                
                auction.status = status
                auction.save()

            auctions.append(auction)
        
        self.stdout.write(f'  Created {len(auctions)} auctions')
        return auctions

    def create_auction_bids(self, auctions, buyers):
        bids_count = 0
        for auction in auctions:
            if auction.status == 'draft' or auction.status == 'cancelled':
                continue
            
            # Determine number of bids based on status
            if auction.status == 'completed':
                num_bids = random.randint(5, 20)
            elif auction.status == 'active':
                num_bids = random.randint(0, 15)
            else:
                num_bids = 0
            
            if num_bids == 0:
                continue
            
            # Check existing bids
            existing_bids = auction.bids.count()
            if existing_bids >= num_bids:
                bids_count += existing_bids
                continue
            
            to_create = num_bids - existing_bids
            current_bid_amount = auction.starting_price
            
            # Create bids in ascending order
            for i in range(to_create):
                buyer = random.choice(buyers)
                
                # Increment bid amount
                current_bid_amount += auction.bid_increment + Decimal(random.randint(0, 5))
                
                bid = Bid.objects.create(
                    auction=auction,
                    bidder=buyer,
                    amount=current_bid_amount,
                    status='active'
                )
                
                # Update auction's current highest bid
                auction.current_highest_bid = current_bid_amount
                auction.current_highest_bidder = buyer
                auction.save()
                
                # Create payment transaction
                PaymentTransaction.objects.create(
                    ticket=None,  # No ticket for auctions
                    amount=current_bid_amount,
                    status='completed',
                    paypal_tx_id=f'test_{bid.id}'
                )
                
                bids_count += 1
            
            # If auction is completed, create result
            if auction.status == 'completed' and auction.bids.filter(status='active').exists():
                highest_bid = auction.bids.filter(status='active').order_by('-amount').first()
                if highest_bid:
                    AuctionResult.objects.create(
                        auction=auction,
                        winner=highest_bid.bidder,
                        winning_bid=highest_bid,
                        final_price=highest_bid.amount,
                        status='completed' if auction.reserve_met else 'no_winner',
                        total_bids=auction.bids.count()
                    )
                    
                    # Mark other bids as outbid
                    auction.bids.filter(status='active').exclude(id=highest_bid.id).update(
                        status='outbid',
                        outbid_at=timezone.now()
                    )
                    highest_bid.status = 'winning'
                    highest_bid.save()
        
        self.stdout.write(f'  Processed {bids_count} bids')
