from django.contrib import admin
from .models import Lottery, LotteryTicket, WinnerDrawing
from .tasks import process_lottery_extraction
from django.contrib import messages
from django.utils.translation import ngettext
from django.utils import timezone
from datetime import timedelta

@admin.register(Lottery)
class LotteryAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'status', 'items_count', 'tickets_sold', 'can_manually_draw', 'created_at')
    list_filter = ('status', 'can_manually_draw', 'created_at', 'kyc_completed')
    search_fields = ('title', 'description', 'seller__email', 'seller__username')
    readonly_fields = ('tickets_sold', 'ticket_price', 'progress_percent')
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
    list_display = ('lottery', 'winner', 'winning_ticket', 'drawn_at', 'status', 'prize_amount')
    list_filter = ('status', 'drawn_at')
    search_fields = ('lottery__title', 'winner__email', 'winner__username', 'winning_ticket__ticket_number')
    readonly_fields = ('drawn_at',)
