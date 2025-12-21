from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from mercato_lotteries.models import Lottery, LotteryTicket
from mercato_payments.models import PaymentMethod, PaymentTransaction
from django.utils import timezone
from decimal import Decimal
import random
from io import BytesIO
from PIL import Image

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with seed data for testing'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding data...')
        
        self.create_payment_methods()
        buyers = self.create_buyers()
        sellers = self.create_sellers()
        lotteries = self.create_lotteries(sellers)
        self.create_sales(lotteries, buyers)
        
        self.stdout.write(self.style.SUCCESS('✅ Seed data created successfully!'))

    def create_dummy_image(self):
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img = Image.new('RGB', (400, 300), color=color)
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer

    def create_payment_methods(self):
        methods = [
            ('PayPal', 'paypal', 3.50),
            ('Credit Card', 'credit_card', 2.00),
        ]
        for name, type, fee in methods:
            PaymentMethod.objects.get_or_create(
                method_type=type,
                defaults={'name': name, 'processing_fee': fee}
            )
        self.stdout.write(f'Created/Checked payment methods')

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
        self.stdout.write(f'Created {len(buyers)} buyers')
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
        self.stdout.write(f'Created {len(sellers)} sellers')
        return sellers

    def create_lotteries(self, sellers):
        lotteries = []
        statuses = ['draft', 'active', 'active', 'active', 'closed', 'active', 'draft', 'closed', 'active', 'active']
        
        for i, status in enumerate(statuses):
            seller = random.choice(sellers)
            title = f'Lottery Item {i+1}'
            item_value = Decimal(random.randint(100, 1000))
            items_count = random.randint(10, 100)
            
            lottery, created = Lottery.objects.get_or_create(
                title=title,
                defaults={
                    'description': f'This is a description for {title}. Great item!',
                    'item_value': item_value,
                    'items_count': items_count,
                    'seller': seller,
                    'status': 'draft', # Create as draft first to avoid signals
                }
            )
            
            # Add images if just created
            if created:
                lottery.set_image_1(self.create_dummy_image())
                lottery.image_1_description = "Front view"
                lottery.set_image_2(self.create_dummy_image())
                lottery.image_2_description = "Side view"
                lottery.set_image_3(self.create_dummy_image())
                lottery.image_3_description = "Detail view"
                
                # Fix kyc if active
                if status == 'active':
                    lottery.kyc_completed = True
                
                lottery.status = status
                lottery.save()

            lotteries.append(lottery)
        
        self.stdout.write(f'Created {len(lotteries)} lotteries')
        return lotteries

    def create_sales(self, lotteries, buyers):
        tickets_count = 0
        for lottery in lotteries:
            if lottery.status == 'draft':
                continue
                
            sold_count = 0
            if lottery.status == 'closed':
                 sold_count = lottery.items_count
            else:
                 # Active: sell some random amount
                 sold_count = random.randint(0, int(lottery.items_count * 0.8))
            
            # Check if we already have enough tickets
            existing_tickets = lottery.tickets.count()
            if existing_tickets >= sold_count:
                tickets_count += existing_tickets
                continue

            to_sell = sold_count - existing_tickets
            
            for _ in range(to_sell):
                buyer = random.choice(buyers)
                
                ticket = LotteryTicket.objects.create(
                    lottery=lottery,
                    buyer=buyer,
                    payment_status='pending'
                )
                
                tx = PaymentTransaction.objects.create(
                    ticket=ticket,
                    amount=lottery.ticket_price,
                    status='pending'
                )
                
                tx.mark_as_completed()
                tickets_count += 1
                
        self.stdout.write(f'Processed {tickets_count} tickets')
