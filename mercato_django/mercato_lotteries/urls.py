from django.urls import path
from . import views

app_name = 'lotteries'

urlpatterns = [
    # Lottery URLs (legacy)
    path('', views.lottery_list, name='list'),
    path('lotteries/', views.lottery_list, name='lottery_list'),
    path('lottery/<int:lottery_id>/', views.lottery_detail, name='detail'),
    path('lottery/<int:lottery_id>/buy-tickets/', views.buy_tickets, name='buy_tickets'),
    path('lottery/<int:lottery_id>/initiate-draw/', views.initiate_draw, name='initiate_draw'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('results/', views.lottery_results, name='results'),
    
    # Auction URLs
    path('auctions/', views.auction_list, name='auction_list'),
    path('auction/<int:auction_id>/', views.auction_detail, name='auction_detail'),
    path('auction/<int:auction_id>/place-bid/', views.place_bid, name='place_bid'),
    path('auction/<int:auction_id>/close/', views.close_auction, name='close_auction'),
    path('auction/<int:auction_id>/cancel/', views.cancel_auction, name='cancel_auction'),
    path('my-bids/', views.my_bids, name='my_bids'),
]