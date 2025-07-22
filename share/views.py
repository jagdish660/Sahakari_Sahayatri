from multiprocessing import Value
from django.forms import CharField
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from share.models import ShareBalance, ShareCapital, ShareRefund
from customer.models import Member, Transaction
from itertools import chain
from operator import attrgetter
from django.db.models import F, Value as DBValue, CharField
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator

# Create your views here.

# /share/
@login_required(login_url='loginpage')
def share_home(request):
    if request.user.is_staff or request.user.is_superuser:
        
        shares = ShareCapital.objects.select_related('customer').all().order_by('-purchase_date')
        total_shares = sum(share.share_amount for share in shares)
        current_year = timezone.now().year
        current_year_shares = sum(
            share.share_amount for share in shares if share.purchase_date.year == current_year
        )
        previous_year_shares = total_shares - current_year_shares
        members = Member.objects.all()
        share = ShareBalance.objects.select_related('customer').all().order_by('-last_updated')
        paginator = Paginator(share, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {
            'share': share,
            'page_obj': page_obj,
            'shares': shares,
            'total_shares': total_shares,
            'current_year_shares': current_year_shares,
            'previous_year_shares': previous_year_shares,
            'members': members,
        }
        return render(request, 'share_home.html', context)
    else:
        return redirect('home')


# /share/add/<int:id>/
@login_required(login_url='loginpage')
def share_add(request, id):
    member = get_object_or_404(Member, member_id=id)
    if request.user.is_staff or request.user.is_superuser:
        if request.method == "POST":
            try:
                raw_amount = request.POST.get('amount')
                amount = Decimal(raw_amount)  # Ensure Decimal conversion

                ShareCapital.objects.create(
                    customer=member,
                    share_amount=int(amount),  # If share_amount is IntegerField
                    purchase_date=timezone.now()
                )

                Transaction.objects.create(
                    member=member,
                    date=timezone.now(),
                    amount=amount,
                    share=amount,
                    remarks=f"Share purchased on {timezone.now()}",
                    payment_method='cash'
                )

                messages.success(request, f"Share purchased successfully for Rs. {amount}.")
                return redirect('customer_details', member_id=member.member_id)

            except (InvalidOperation, ValueError):
                messages.error(request, "Invalid amount. Please enter a valid number.")
                return redirect('customer_details', member_id=member.member_id)

            except Exception as e:
                messages.error(request, f"Error occurred: {e}")
                print(e)
                return redirect('customer_details', member_id=member.member_id)

        return render(request, 'share_add.html', {'member': member})

    else:
        messages.error(request, "You're not authorized to perform this action.")
        return redirect('home')


# /share/refund/<int:id>/
@login_required(login_url='loginpage')
def share_refund(request, id):
    member = get_object_or_404(Member, member_id=id)
    if request.user.is_superuser or request.user.is_staff:
        if request.method == "POST":
            try:
                amount = Decimal(request.POST.get('amount'))
                # Get the current share balance
                share_balance_obj = ShareBalance.objects.filter(customer=member).first()
                current_balance = Decimal(share_balance_obj.balance) if share_balance_obj else Decimal('0.00')
                if amount <= 0:
                    messages.error(request, "Refund amount must be positive.")
                elif amount > current_balance:
                    messages.error(request, f"Refund amount exceeds available shares. Available: {current_balance}")
                else:
                    ShareRefund.objects.create(
                        customer=member,
                        refund_amount=int(amount),
                        refund_date=timezone.now()
                    )
                    Transaction.objects.create(
                        member=member,
                        date=timezone.now(),
                        amount=Decimal('0.00'),
                        share=-amount,
                        remarks=f"Share refund of Rs. {amount} on {timezone.now().date()}"
                    )
                    messages.success(request, f"Successfully refunded Rs. {amount} from shares.")
                    return redirect('share_home')
            except Exception as e:
                messages.error(request, f"Error: {e}")
                print(e)
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('share_home')
    return render(request, 'share_refund.html', {'member': member})


# /share/<int:id>/
@login_required(login_url='loginpage')
def share_details(request, id):
    member = Member.objects.filter(member_id=id).first()
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


#  /share/add/
@login_required(login_url='loginpage')
def share_add_individual(request):
    if request.user.is_staff or request.user.is_superuser:

        members = Member.objects.all()
        if request.method == 'POST':
            member_id = request.POST.get('member_id')
            amount = request.POST.get('amount')
            # Validation
            if not member_id or not member_id.isdigit():
                messages.error(request, "Please select a valid member.")
                return render(request, 'share_add_individual.html', {'members': members})
            if not amount:
                messages.error(request, "Please enter a valid amount.")
                return render(request, 'share_add_individual.html', {'members': members})
            try:
                customer = Member.objects.get(pk=int(member_id))
                ShareCapital.objects.create(
                    customer=customer,
                    share_amount=Decimal(amount),
                    purchase_date=timezone.now()
                )
                messages.success(request, f"Share successfully added for {customer.name}.")
                return redirect('share_home')
            except Member.DoesNotExist:
                messages.error(request, "Member not found.")
            except Exception as e:
                messages.error(request, f"Error occurred: {e}")
        return render(request, 'share_add_individual.html', {'members': members})
    else:
        return redirect('home')