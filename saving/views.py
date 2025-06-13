from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import date
from django.db import models
from customer.models import Member
from saving.models import Deposit, YearlyInterest, SavingRefund
from django.core.paginator import Paginator

# Create your views here.
def get_fiscal_year_start():
    today = date.today()
    if today.month > 7 or (today.month == 7 and today.day >= 16):  # Assuming Shrawan 1 is around July 16
        return date(today.year, 7, 16)
    else:
        return date(today.year - 1, 7, 16)

from django.core.paginator import Paginator
from django.db.models import Sum

def saving_home(request):
    fiscal_year_start = get_fiscal_year_start()
    members = Member.objects.all()

    # total amount saved by all members 
    depos = Deposit.objects.all()
    refu = SavingRefund.objects.all()

    customer_data = []
    total_previous_saving = 0
    total_current_saving = 0  
    total_saved = 0

    for member in members:
        deposits = Deposit.objects.filter(customer=member)
        refunds = SavingRefund.objects.filter(customer=member)

        previous_saving = deposits.filter(date__lt=fiscal_year_start).aggregate(total=Sum('amount'))['total'] or 0
        current_saving = deposits.filter(date__gte=fiscal_year_start).aggregate(total=Sum('amount'))['total'] or 0
        total_refunded = refunds.aggregate(total=Sum('amount_refunded'))['total'] or 0

        total_saving = previous_saving + current_saving - total_refunded

        total_previous_saving += previous_saving  # Accumulate here
        total_current_saving += current_saving  # Accumulate here
        total_saved += total_saving  # Accumulate here

        customer_data.append({
            'id': member.member_id,
            'name': member.name,
            'previous_saving': previous_saving,
            'current_saving': current_saving,
            'total_refunded': total_refunded,
            'total_saving': total_saving
        })

    paginator = Paginator(customer_data,20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'saving_home.html', {
        'customer_data': customer_data,
        'total_saved': total_saved,
        'total_previous_saving': total_previous_saving,  # Pass to template
        'total_current_saving': total_current_saving,
        'page_obj': page_obj
    })

def transactions(request):
    return render(request, 'transactions.html')


def saving_details(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    
    deposits = Deposit.objects.filter(customer=member).order_by('date')
    refunds = SavingRefund.objects.filter(customer=member).order_by('refund_date')
    interests = YearlyInterest.objects.filter(customer=member).order_by('year')
    
    transactions = []
    for deposit in deposits:
        transactions.append({
            'date': deposit.date,
            'type': 'Deposit',
            'amount': deposit.amount,
            'payment_method': deposit.payment_method,
            'remarks': deposit.remarks,
        })
    for refund in refunds:
        transactions.append({
            'date': refund.refund_date,
            'type': 'Refund',
            'amount': -refund.amount_refunded,
            'payment_method': refund.payment_method,
            'remarks': refund.remarks,
        })
    for interest in interests:
        total_interest = interest.previous_interest_amount + interest.current_interest_amount
        transactions.append({
            'date': interest.date,
            'type': 'Interest',
            'amount': total_interest,  # use total_interest from interest calculation
            # 'interest_amount': total_interest,  # explicitly pass interest amount
            'payment_method': 'Auto',
            'remarks': f"Interest for FY {interest.year}",
        })

    transactions.sort(key=lambda x: x['date'])

    METHOD_DISPLAY = {
        'cash': 'Cash',
        'bank_transfer': 'Bank Transfer',
        'cheque': 'Cheque',
        'Auto': 'Interest',
    }

    running_balance = 0
    detailed_transactions = []
    for tx in transactions:
        previous_balance = running_balance
        running_balance += tx['amount']
        detailed_transactions.append({
            'member_id': member_id,
            'date': tx['date'],
            'type': tx['type'],
            'amount': abs(tx['amount']),
            'interest_amount': tx.get('interest_amount', None),  # may be None for non-interest tx
            'previous_balance': previous_balance,
            'balance': running_balance,
            'payment_method': METHOD_DISPLAY.get(tx['payment_method'], tx['payment_method']),
            'remarks': tx['remarks'],
        })

    return render(request, 'saving_details.html', {
        'member': member,
        'transactions': detailed_transactions
    })


def saving_yearly_interest(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    interests = YearlyInterest.objects.filter(customer=member).order_by('year')

    interest_data = []
    for interest in interests:
        interest_values = interest.calculate_interest()
        interest_data.append({
            'year': interest.year,
            'pre_balance': interest_values['pre_balance'],
            'post_balance': interest_values['post_balance'],
            'pre_interest': interest_values['pre_interest'],
            'post_interest': interest_values['post_interest'],
            'total_interest': interest_values['total_interest'],
        })

    return render(request, 'saving_yearly_interest.html', {
        'member': member,
        'interest_data': interest_data
    })

