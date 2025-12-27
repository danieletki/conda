from django.urls import path
from . import views

app_name = 'mercato_lotteries'

urlpatterns = [
    path('', views.lottery_list, name='list'),
    path('<int:lottery_id>/', views.lottery_detail, name='detail'),
    path('<int:lottery_id>/buy-tickets/', views.buy_tickets, name='buy_tickets'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('results/', views.lottery_results, name='results'),
]