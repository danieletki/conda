from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion
import uuid

import mercato_lotteries.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Lottery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('item_value', models.DecimalField(decimal_places=2, max_digits=15, validators=[MinValueValidator(0.01)])),
                ('items_count', models.PositiveIntegerField(validators=[MinValueValidator(1)])),
                ('ticket_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('draft', 'Bozza'),
                            ('active', 'Attiva'),
                            ('closed', 'Chiusa'),
                            ('drawn', 'Estrazione Eseguita'),
                            ('completed', 'Completata'),
                        ],
                        default='draft',
                        max_length=20,
                    ),
                ),
                ('kyc_completed', models.BooleanField(default=False)),
                ('expiration_date', models.DateTimeField(blank=True, null=True)),
                ('image_1', mercato_lotteries.models.CompressedImageField()),
                ('image_2', mercato_lotteries.models.CompressedImageField()),
                ('image_3', mercato_lotteries.models.CompressedImageField()),
                ('image_1_description', models.CharField(blank=True, max_length=255)),
                ('image_2_description', models.CharField(blank=True, max_length=255)),
                ('image_3_description', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'seller',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='lotteries_as_seller',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LotteryTicket',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('ticket_number', models.CharField(max_length=20, unique=True)),
                ('purchased_at', models.DateTimeField(auto_now_add=True)),
                (
                    'payment_status',
                    models.CharField(
                        choices=[
                            ('pending', 'In attesa'),
                            ('payment_processing', 'Elaborazione pagamento'),
                            ('payment_failed', 'Pagamento fallito'),
                            ('completed', 'Completato'),
                            ('refunded', 'Rimborsato'),
                        ],
                        default='pending',
                        max_length=20,
                    ),
                ),
                (
                    'buyer',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='purchased_tickets',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'lottery',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tickets',
                        to='mercato_lotteries.lottery',
                    ),
                ),
            ],
            options={
                'ordering': ['-purchased_at'],
                'unique_together': {('lottery', 'buyer', 'ticket_number')},
            },
        ),
        migrations.CreateModel(
            name='WinnerDrawing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drawn_at', models.DateTimeField(auto_now_add=True)),
                (
                    'status',
                    models.CharField(
                        choices=[('pending', 'In attesa'), ('completed', 'Completato'), ('cancelled', 'Annullato')],
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('prize_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                (
                    'lottery',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='drawings',
                        to='mercato_lotteries.lottery',
                    ),
                ),
                (
                    'winner',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='won_lotteries',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'winning_ticket',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to='mercato_lotteries.lotteryticket',
                    ),
                ),
            ],
            options={
                'ordering': ['-drawn_at'],
            },
        ),
        migrations.AddIndex(
            model_name='lottery',
            index=models.Index(fields=['status', 'created_at'], name='mercato_lo_status_7a9a5f_idx'),
        ),
        migrations.AddIndex(
            model_name='lottery',
            index=models.Index(fields=['seller', 'status'], name='mercato_lo_seller_709b23_idx'),
        ),
        migrations.AddIndex(
            model_name='winnerdrawing',
            index=models.Index(fields=['status', 'drawn_at'], name='mercato_lo_status_e2b8f1_idx'),
        ),
    ]
