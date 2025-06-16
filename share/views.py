from multiprocessing import Value
from django.forms import CharField
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from share.models import ShareBalance, ShareCapital, ShareRefund
from customer.models import Member
from itertools import chain
from operator import attrgetter
from django.db.models import F, Value as DBValue, CharField

# Create your views here.

# /share/
@login_required(login_url='loginpage')
def share_home(request):
    shares = ShareCapital.objects.select_related('customer').all().order_by('-purchase_date')
    total_shares = sum(share.share_amount for share in shares)
    current_year = timezone.now().year
    current_year_shares = sum(
        share.share_amount for share in shares if share.purchase_date.year == current_year
    )
    previous_year_shares = total_shares - current_year_shares
    members = Member.objects.all()
    share = ShareBalance.objects.select_related('customer').all().order_by('-last_updated')
    context = {
        'share': share,
        'shares': shares,
        'total_shares': total_shares,
        'current_year_shares': current_year_shares,
        'previous_year_shares': previous_year_shares,
        'members': members,
    }
    return render(request, 'share_home.html', context)



# /share/<int:id>/
@login_required(login_url='loginpage')
def share_details(request, id):
    member = Member.objects.filter(member_id=id).first()
    print(id)
    print(member)
    if not member:
        # Handle not found member properly (redirect or 404)
        return render(request, 'share_details.html', {'error': 'Member not found.'})
    # Query purchases and refunds
    
    purchases = ShareCapital.objects.filter(customer=member).annotate(
        transaction_date=F('purchase_date'),
        transaction_type=DBValue('purchase', output_field=CharField(max_length=20)),
        transaction_amount=F('share_amount')
    ).values('transaction_date', 'transaction_type', 'transaction_amount')

    refunds = ShareRefund.objects.filter(customer=member).annotate(
        transaction_date=F('refund_date'),
        transaction_type=DBValue('refund', output_field=CharField(max_length=20)),
        transaction_amount=F('refund_amount')
    ).values('transaction_date', 'transaction_type', 'transaction_amount')

    # Combine and order by date
    transactions = sorted(
        list(purchases) + list(refunds),
        key=lambda x: x['transaction_date']
    )
    # Calculate previous_balance for each transaction
    prev_balance = 0
    for tx in transactions:
        tx['previous_balance'] = prev_balance
        if tx['transaction_type'] == 'purchase':
            tx['balance_after'] = prev_balance + tx['transaction_amount']
        else:
            tx['balance_after'] = prev_balance - tx['transaction_amount']
        prev_balance = tx['balance_after']
    context = {
        'member': member,
        'transactions': transactions,
    }
    return render(request, 'share_details.html', context)

