# Generated migration for Auction system models

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('mercato_lotteries', '0005_lottery_regione_categoria_fks'),
        ('auth', '0012_alter_user_first_name_max_length'),  # Django 4.2
    ]

    operations = [
        # Create Auction model
        migrations.CreateModel(
            name='Auction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('item_value', models.DecimalField(decimal_places=2, max_digits=15, validators=[django.core.validators.MinValueValidator(0.01)])),
                # Auction-specific fields
                ('starting_price', models.DecimalField(decimal_places=2, max_digits=15, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('reserve_price', models.DecimalField(decimal_places=2, max_digits=15, null=True, blank=True, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('bid_increment', models.DecimalField(decimal_places=2, default=10.0, max_digits=10, validators=[django.core.validators.MinValueValidator(1.0)])),
                ('auction_end_time', models.DateTimeField(null=True, blank=True)),
                ('current_highest_bid', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('status', models.CharField(choices=[('draft', 'Bozza'), ('active', 'Attiva'), ('paused', 'In Pausa'), ('closed', 'Chiusa'), ('completed', 'Completata'), ('cancelled', 'Annullata')], default='draft', max_length=20)),
                ('kyc_completed', models.BooleanField(default=False)),
                ('auto_close_on_end_time', models.BooleanField(default=True, help_text="Chiudi automaticamente l'asta quando scade il tempo")),
                # Compressed images
                ('image_1', models.BinaryField(blank=True, null=True)),
                ('image_2', models.BinaryField(blank=True, null=True)),
                ('image_3', models.BinaryField(blank=True, null=True)),
                # Image descriptions
                ('image_1_description', models.CharField(blank=True, max_length=255)),
                ('image_2_description', models.CharField(blank=True, max_length=255)),
                ('image_3_description', models.CharField(blank=True, max_length=255)),
                # Timestamps
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('closed_at', models.DateTimeField(null=True, blank=True)),
                # Foreign keys
                ('regione', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='mercato_lotteries.regione')),
                ('categoria', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='mercato_lotteries.categoria')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auctions_as_seller', to='auth.user')),
                ('current_highest_bidder', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='winning_auctions', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'mercato_lotteries_auction',
                'indexes': [
                    models.Index(fields=['status', 'created_at'], name='mercato_auc_status_idx'),
                    models.Index(fields=['seller', 'status'], name='mercato_auc_seller_idx'),
                    models.Index(fields=['auction_end_time'], name='mercato_auc_end_time_idx'),
                    models.Index(fields=['current_highest_bid'], name='mercato_auc_highest_idx'),
                ],
            },
        ),

        # Create Bid model
        migrations.CreateModel(
            name='Bid',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('status', models.CharField(choices=[('pending', 'In Attesa'), ('active', 'Attiva'), ('outbid', 'Superata'), ('winning', 'Vincente'), ('refunded', 'Rimborsata'), ('cancelled', 'Annullata')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('outbid_at', models.DateTimeField(null=True, blank=True)),
                ('refunded_at', models.DateTimeField(null=True, blank=True)),
                # Foreign keys
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bids', to='mercato_lotteries.auction')),
                ('bidder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auction_bids', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'mercato_lotteries_bid',
                'indexes': [
                    models.Index(fields=['auction', 'status'], name='mercato_bid_auc_idx'),
                    models.Index(fields=['bidder', 'status'], name='mercato_bid_bidder_idx'),
                    models.Index(fields=['amount'], name='mercato_bid_amount_idx'),
                ],
            },
        ),

        # Create AuctionResult model
        migrations.CreateModel(
            name='AuctionResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('final_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('status', models.CharField(choices=[('completed', 'Completato'), ('no_winner', 'Nessun Vincitore'), ('cancelled', 'Annullato')], default='completed', max_length=20)),
                ('determined_at', models.DateTimeField(auto_now_add=True)),
                ('total_bids', models.PositiveIntegerField(default=0)),
                ('total_refunded_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('cancellation_reason', models.TextField(blank=True, null=True)),
                ('is_shipped', models.BooleanField(default=False, help_text="Se il premio è stato spedito al vincitore")),
                ('shipped_at', models.DateTimeField(blank=True, null=True, help_text="Data e ora di spedizione del premio")),
                # Foreign keys
                ('auction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result', to='mercato_lotteries.auction')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_auctions', to='auth.user')),
                ('winning_bid', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='mercato_lotteries.bid')),
            ],
            options={
                'ordering': ['-determined_at'],
                'db_table': 'mercato_lotteries_auctionresult',
                'indexes': [
                    models.Index(fields=['status', 'determined_at'], name='mercato_ares_status_idx'),
                ],
            },
        ),
    ]
