from django.contrib import admin
from .models import Lottery, LotteryTicket, WinnerDrawing
from .tasks import process_lottery_extraction
from django.contrib import messages
from django.utils.translation import ngettext

@admin.register(Lottery)
class LotteryAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'status', 'items_count', 'tickets_sold', 'expiration_date', 'created_at')
    list_filter = ('status', 'created_at', 'kyc_completed')
    search_fields = ('title', 'description', 'seller__email', 'seller__username')
    readonly_fields = ('tickets_sold', 'ticket_price', 'progress_percent')
    actions = ['extract_winner_manually']
    
    @admin.action(description='Estrai vincitore manualmente (per lotterie chiuse)')
    def extract_winner_manually(self, request, queryset):
        count = 0
        for lottery in queryset:
            if lottery.status == 'closed' and not lottery.drawings.exists():
                # Trigger the Celery task
                process_lottery_extraction.delay(lottery.id)
                count += 1
            else:
                self.message_user(request, f"Lotteria {lottery.title} ignorata: deve essere 'closed' e senza estrazioni.", level=messages.WARNING)
        
        if count:
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
