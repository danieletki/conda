from django.urls import path
from . import views

app_name = 'lotteries'

urlpatterns = [
    path('', views.lottery_list, name='list'),
    path('<int:lottery_id>/', views.lottery_detail, name='detail'),
    path('<int:lottery_id>/place-bid/', views.place_bid, name='place_bid'),
    path('auction/<int:lottery_id>/close/', views.close_auction_view, name='close_auction'),
    path('my-bids/', views.my_bids, name='my_bids'),
    path('results/', views.lottery_results, name='results'),
]

# Backwards compatibility URL aliases
urlpatterns += [
    path('<int:lottery_id>/buy-tickets/', views.place_bid, name='buy_tickets'),
    path('my-tickets/', views.my_bids, name='my_tickets'),
]
