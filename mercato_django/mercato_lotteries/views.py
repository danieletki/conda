from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Lottery, LotteryTicket


def lottery_list(request):
    """
    Display list of available lotteries
    """
    lotteries = Lottery.objects.filter(status='active').order_by('-created_at')
    categories = Category.objects.filter(is_active=True)
    
    # Filter by category if specified
    category = request.GET.get('category')
    if category:
        lotteries = lotteries.filter(category_id=category)
    
    return render(request, 'lotteries/list.html', {
        'lotteries': lotteries,
        'categories': categories,
        'selected_category': category
    })


def lottery_detail(request, lottery_id):
    """
    Display lottery details
    """
    try:
        lottery = Lottery.objects.get(id=lottery_id, status='active')
        user_tickets = []
        
        if request.user.is_authenticated:
            user_tickets = LotteryTicket.objects.filter(
                lottery=lottery, 
                user=request.user
            )
        
        return render(request, 'lotteries/detail.html', {
            'lottery': lottery,
            'user_tickets': user_tickets
        })
    except Lottery.DoesNotExist:
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Lottery, id=lottery_id)


@login_required
def buy_tickets(request, lottery_id):
    """
    Buy tickets for a lottery
    """
    # This will be implemented when payment integration is ready
    return render(request, 'lotteries/buy_tickets.html')


@login_required
def my_tickets(request):
    """
    Display user's purchased tickets
    """
    tickets = LotteryTicket.objects.filter(user=request.user).order_by('-purchase_date')
    return render(request, 'lotteries/my_tickets.html', {'tickets': tickets})


def lottery_results(request):
    """
    Display lottery results
    """
    # This will be implemented when lottery results are generated
    return render(request, 'lotteries/results.html')