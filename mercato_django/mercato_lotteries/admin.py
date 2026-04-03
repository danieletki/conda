from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import ngettext

from .models import Categoria, Auction, Bid, Regione, AuctionResult
from .tasks import close_auction


@admin.register(Regione)
class RegioneAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.pk == 1:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'seller', 'regione', 'categoria', 'status',
        'starting_price', 'current_price', 'auction_end_time', 'created_at',
    )
    list_filter = ('status', 'regione', 'categoria', 'created_at', 'kyc_completed')
    search_fields = ('title', 'description', 'seller__email', 'seller__username', 'regione__name', 'categoria__name')
    readonly_fields = ('created_at', 'updated_at', 'current_price', 'bids_count', 'unique_bidders_count')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'regione', 'categoria', 'seller', 'status')}),
        ('Valori Asta', {'fields': ('item_value', 'starting_price', 'reserve_price', 'bid_increment', 'auction_end_time')}),
        ('Configurazione', {'fields': ('kyc_completed',)}),
        ('Immagini', {'fields': ('image_1_description', 'image_2_description', 'image_3_description')}),
        ('Statistiche', {'fields': ('current_price', 'bids_count', 'unique_bidders_count', 'created_at', 'updated_at')}),
    )
    actions = ['close_auction_manually']

    @admin.action(description='Chiudi asta manualmente')
    def close_auction_manually(self, request, queryset):
        count = 0
        for auction in queryset:
            if auction.status != 'active':
                self.message_user(request, f"Asta {auction.title} ignorata: non è attiva.", messages.WARNING)
                continue
            if not auction.bids.exists():
                self.message_user(request, f"Asta {auction.title} ignorata: non ci sono offerte.", messages.WARNING)
                continue
            close_auction.delay(auction.id)
            count += 1
        
        if count > 0:
            self.message_user(request, ngettext('%d asta in chiusura.', '%d aste in chiusura.', count) % count, messages.SUCCESS)


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('id', 'auction', 'bidder', 'amount', 'status', 'is_highest', 'placed_at')
    list_filter = ('status', 'is_highest', 'placed_at')
    search_fields = ('auction__title', 'bidder__email', 'bidder__username')
    readonly_fields = ('placed_at',)


@admin.register(AuctionResult)
class AuctionResultAdmin(admin.ModelAdmin):
    list_display = ('auction', 'winner', 'winning_bid', 'final_price', 'closed_at', 'status', 'is_shipped')
    list_filter = ('status', 'is_shipped', 'closed_at')
    search_fields = ('auction__title', 'winner__email', 'winner__username')
    readonly_fields = ('closed_at', 'shipped_at')
    raw_id_fields = ('auction', 'winner', 'winning_bid')


# Backwards compatibility aliases
LotteryAdmin = AuctionAdmin
LotteryTicketAdmin = BidAdmin
WinnerDrawingAdmin = AuctionResultAdmin
