from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import ngettext

from .models import Categoria, Lottery, LotteryTicket, Regione, WinnerDrawing
from .tasks import process_lottery_extraction


@admin.register(Regione)
class RegioneAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.pk == 1:
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        if obj.pk == 1:
            self.message_user(
                request,
                "La regione 'Non Specificato' non può essere eliminata.",
                level=messages.ERROR,
            )
            return
        return super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if queryset.filter(pk=1).exists():
            self.message_user(
                request,
                "La regione 'Non Specificato' non può essere eliminata.",
                level=messages.ERROR,
            )
        return super().delete_queryset(request, queryset.exclude(pk=1))


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Lottery)
class LotteryAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'seller',
        'regione',
        'categoria',
        'status',
        'items_count',
        'tickets_sold',
        'can_manually_draw',
        'created_at',
    )
    list_filter = (
        'status',
        'regione',
        'categoria',
        'can_manually_draw',
        'created_at',
        'kyc_completed',
    )
    search_fields = (
        'title',
        'description',
        'seller__email',
        'seller__username',
        'regione__name',
        'categoria__name',
    )
    readonly_fields = ('tickets_sold', 'ticket_price', 'progress_percent', 'created_at', 'updated_at')
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'title',
                    'description',
                    'regione',
                    'categoria',
                    'seller',
                    'status',
                    'expiration_date',
                )
            },
        ),
        (
            'Valori',
            {'fields': ('item_value', 'items_count', 'ticket_price')},
        ),
        (
            'Configurazione',
            {'fields': ('can_manually_draw', 'min_draw_delay_hours', 'kyc_completed')},
        ),
        (
            'Immagini',
            {
                'fields': (
                    'image_1_description',
                    'image_2_description',
                    'image_3_description',
                )
            },
        ),
        (
            'Metadati',
            {'fields': ('tickets_sold', 'progress_percent', 'created_at', 'updated_at')},
        ),
    )
    actions = ['extract_winner_manually']

    @admin.action(description='Estrai vincitore manualmente')
    def extract_winner_manually(self, request, queryset):
        """
        Manually trigger winner extraction for eligible lotteries.
        Eligibility criteria:
        - Manual draw is enabled (can_manually_draw=True)
        - Minimum draw delay has passed since creation
        - No drawing exists yet
        """
        count = 0
        for lottery in queryset:
            # Check if manual drawing is enabled
            if not lottery.can_manually_draw:
                self.message_user(
                    request, 
                    f"Lotteria {lottery.title} ignorata: l'estrazione manuale non è abilitata.", 
                    level=messages.WARNING
                )
                continue
            
            # Check if minimum draw delay has passed
            min_draw_time = lottery.created_at + timedelta(hours=lottery.min_draw_delay_hours)
            if timezone.now() < min_draw_time:
                self.message_user(
                    request, 
                    f"Lotteria {lottery.title} ignorata: è necessario attendere {lottery.min_draw_delay_hours}h dalla creazione.", 
                    level=messages.WARNING
                )
                continue
            
            # Check if drawing already exists
            if lottery.drawings.exists():
                self.message_user(
                    request, 
                    f"Lotteria {lottery.title} ignorata: l'estrazione è già stata eseguita.", 
                    level=messages.WARNING
                )
                continue
            
            # Check if there are any completed tickets
            if not lottery.tickets.filter(payment_status='completed').exists():
                self.message_user(
                    request, 
                    f"Lotteria {lottery.title} ignorata: non ci sono biglietti pagati.", 
                    level=messages.WARNING
                )
                continue
            
            # All checks passed - trigger extraction
            process_lottery_extraction.delay(lottery.id)
            count += 1
        
        if count > 0:
            self.message_user(request, ngettext(
                '%d estrazione avviata.',
                '%d estrazioni avviate.',
                count,
            ) % count, messages.SUCCESS)

@admin.register(LotteryTicket)
class LotteryTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'lottery', 'buyer', 'payment_status', 'purchased_at')
    list_filter = ('payment_status', 'purchased_at')
    search_fields = ('ticket_number', 'lottery__title', 'buyer__email', 'buyer__username')

@admin.register(WinnerDrawing)
class WinnerDrawingAdmin(admin.ModelAdmin):
    list_display = ('lottery', 'winner', 'winning_ticket', 'drawn_at', 'status', 'prize_amount', 'is_shipped', 'shipped_at')
    list_filter = ('status', 'is_shipped', 'drawn_at')
    search_fields = ('lottery__title', 'winner__email', 'winner__username', 'winning_ticket__ticket_number')
    readonly_fields = ('drawn_at', 'shipped_at')

    raw_id_fields = ('lottery', 'winner', 'winning_ticket')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-drawn_at')
