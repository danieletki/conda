from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Lottery, LotteryTicket


def lottery_list(request):
    lotteries_qs = (
        Lottery.objects.filter(status='active')
        .annotate(
            tickets_sold_count=Count(
                'tickets', filter=Q(tickets__payment_status='completed')
            )
        )
        .order_by('-created_at')
    )

    query = (request.GET.get('q') or '').strip()
    if query:
        lotteries_qs = lotteries_qs.filter(title__icontains=query)

    paginator = Paginator(lotteries_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'lotteries/list.html',
        {
            'page_obj': page_obj,
            'lotteries': page_obj.object_list,
            'query': query,
            'categories': [],
            'selected_category': None,
        },
    )


def lottery_detail(request, lottery_id):
    lottery = get_object_or_404(
        Lottery.objects.annotate(
            tickets_sold_count=Count(
                'tickets', filter=Q(tickets__payment_status='completed')
            )
        ),
        id=lottery_id,
        status='active',
    )

    user_tickets = []
    if request.user.is_authenticated:
        user_tickets = (
            LotteryTicket.objects.filter(lottery=lottery, buyer=request.user)
            .order_by('-purchased_at')
            .all()
        )

    return render(
        request,
        'lotteries/detail.html',
        {
            'lottery': lottery,
            'user_tickets': user_tickets,
        },
    )


@login_required
def buy_tickets(request, lottery_id):
    lottery = get_object_or_404(Lottery, id=lottery_id, status='active')
    return render(request, 'lotteries/buy_tickets.html', {'lottery': lottery})


@login_required
def my_tickets(request):
    tickets = (
        LotteryTicket.objects.filter(buyer=request.user)
        .select_related('lottery')
        .order_by('-purchased_at')
    )
    return render(request, 'lotteries/my_tickets.html', {'tickets': tickets})


def lottery_results(request):
    return render(request, 'lotteries/results.html')
