from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from datetime import date
from share.models import ShareCapital
from customer.models import Member, Transaction
from loan.models import Loan, Repayment
from saving.models import Deposit, YearlyInterest, SavingRefund, SavingBalance, OtherFee, get_fiscal_year_starting_shrawan, get_fiscal_year_start_end
from saving.forms import SavingAddForm
from django.core.paginator import Paginator
from django.db.models import Sum
from decimal import Decimal, ROUND_HALF_UP


# Create your views here.
def get_fiscal_year_start():
    today = date.today()
    if today.month > 7 or (today.month == 7 and today.day >= 16):  # Assuming Shrawan 1 is around July 16
        return date(today.year, 7, 16)
    else:
        return date(today.year - 1, 7, 16)


# /
@login_required(login_url='loginpage')
def home(request):
    return render(request, 'home.html')


# /saving/
@login_required(login_url='loginpage')
def saving_home(request):
    fiscal_year_start = get_fiscal_year_start()
    members = Member.objects.all()

    customer_data = []
    total_previous_saving = 0
    total_current_saving = 0  
    total_saved = 0
    for member in members:
        deposits = Deposit.objects.filter(customer=member)
        refunds = SavingRefund.objects.filter(customer=member)
        interest = YearlyInterest.objects.filter(customer=member)
        previous_saving = deposits.filter(date__lt=fiscal_year_start).aggregate(total=Sum('amount'))['total'] or 0
        current_saving = deposits.filter(date__gte=fiscal_year_start).aggregate(total=Sum('amount'))['total'] or 0
        total_refunded = refunds.aggregate(total=Sum('amount_refunded'))['total'] or 0
        total_previous_interest = interest.aggregate(total=Sum('previous_interest_amount'))['total'] or 0
        total_current_interest = interest.aggregate(total=Sum('current_interest_amount'))['total'] or 0
        total_interest = total_current_interest + total_previous_interest
        total_saving = previous_saving + current_saving - total_refunded + total_previous_interest + total_current_interest
        total_previous_saving += previous_saving  # Accumulate here
        total_current_saving += current_saving  # Accumulate here
        total_saved += total_saving  # Accumulate here
        if member.middle_name:
            name=f"{member.first_name} {member.middle_name} {member.last_name}"
        else:
            name=f"{member.first_name} {member.last_name}"
        customer_data.append({
            'id': member.member_id,
            'name': name,
            'previous_saving': previous_saving,
            'current_saving': current_saving,
            'total_refunded': total_refunded,
            'total_saving': total_saving,
        'total_interest': total_interest,
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


# /
@login_required(login_url='loginpage')
def transactions(request):
    loans = Loan.objects.select_related('customer').all().order_by('-id')
    savings = Deposit.objects.select_related('customer').all().order_by('-date')
    interest = YearlyInterest.objects.select_related('customer').all().order_by('-date')
    share_balances = ShareCapital.objects.select_related('customer').all().order_by('-id')
    members = Member.objects.all()
    # Calculate totals of Loans
    total_deployed = sum(loan.amount for loan in loans)
    current_year = timezone.now().year
    deployed_current_year = sum(
        loan.amount for loan in loans if loan.start_date.year == current_year
    )
    deployed_previous_year = total_deployed - deployed_current_year
    # Calculate totals of Savings
    total_savings = sum(deposit.amount for deposit in savings) + sum(i.previous_interest_amount+i.current_interest_amount for i in interest)
    current_year_savings = sum(
        deposit.amount for deposit in savings if deposit.date.year == current_year
    )
    previous_year_savings = total_savings - current_year_savings
    # Calculate totalls for share balance
    total_shares = sum(balance.share_amount for balance in share_balances)
    current_year_shares = sum( 
        balance.share_amount for balance in share_balances if balance.purchase_date.year == current_year
    )
    previous_year_shares = total_shares - current_year_shares
    # Calculate totals of members
    total_members = members.count()
    # Calculate balance
    balance_now = total_savings - total_deployed + total_shares
    context = {
        'loans': loans,
        'total_deployed': total_deployed,
        'deployed_current_year': deployed_current_year,
        'deployed_previous_year': deployed_previous_year,
        'savings': savings,
        'total_savings': total_savings,
        'current_year_savings': current_year_savings,
        'previous_year_savings': previous_year_savings,
        'share_balances': share_balances,
        'total_shares': total_shares,
        'current_year_shares': current_year_shares,
        'previous_year_shares': previous_year_shares,
        'total_members': total_members,
        'members': members,
        'balance_now': balance_now,
    }
    return render(request, 'transactions.html', context)


# /saving/<member_id>/
@login_required(login_url='loginpage')
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
    print(total_interest)
    paginator = Paginator(detailed_transactions,25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'saving_details.html', {
        'member': member,
        'page_obj': page_obj,
        'transactions': detailed_transactions,
    })


# /saving/<member_id>/yearly_interest/
@login_required(login_url='loginpage')
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


# /saving/interest/ 
def saving_interest(request):
    if request.method == 'POST':
        try:
            previous_rate = Decimal(request.POST.get('previous_rate'))
            current_rate = Decimal(request.POST.get('current_rate'))

            current_date = date.today()
            fiscal_year = get_fiscal_year_starting_shrawan(current_date)  # e.g., 2025
            fiscal_year_start_date, fiscal_year_end_date = get_fiscal_year_start_end(fiscal_year)

            customers = Member.objects.all()
            success_count = 0
            error_count = 0

            for customer in customers:
                # Check if interest for this fiscal year already exists
                if not YearlyInterest.objects.filter(customer=customer, year=fiscal_year).exists():
                    try:
                        # Sum of deposits before fiscal year start
                        previous_saving = Deposit.objects.filter(
                            customer=customer,
                            date__lt=fiscal_year_start_date
                        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

                        # Sum of deposits from fiscal year start onwards
                        current_saving = Deposit.objects.filter(
                            customer=customer,
                            date__gte=fiscal_year_start_date
                        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

                        # Calculate interest amounts
                        previous_interest = (previous_saving * previous_rate / Decimal('100')).quantize(Decimal('0.01'))
                        current_interest = (current_saving * current_rate / Decimal('100')).quantize(Decimal('0.01'))

                        # Update or create saving balance
                        balance_obj, _ = SavingBalance.objects.get_or_create(customer=customer)
                        balance_obj.balance += previous_interest + current_interest
                        balance_obj.save()

                        # Create YearlyInterest record
                        YearlyInterest.objects.create(
                            customer=customer,
                            year=fiscal_year,
                            previous_interest_rate=previous_rate,
                            previous_interest_amount=previous_interest,
                            current_interest_rate=current_rate,
                            current_interest_amount=current_interest,
                            remarks=f"Interest for FY {fiscal_year}"
                        )
                        
                        Transaction.objects.create(
                            member=customer,
                            interest_paid=(current_interest + previous_interest),
                            payment_method="interest",
                            remarks=f"Interest credited for FY {fiscal_year}",
                        )

                        # Debug prints (can remove or comment out in production)
                        print(f"Customer: {customer.name}")
                        print(f"Previous Saving: Rs. {previous_saving}")
                        print(f"Previous Interest ({previous_rate}%): Rs. {previous_interest}")
                        print(f"Current Saving: Rs. {current_saving}")
                        print(f"Current Interest ({current_rate}%): Rs. {current_interest}")
                        print(f"Updated Balance: Rs. {balance_obj.balance}\n")

                        success_count += 1
                    except Exception as e:
                        print(f"Error processing {customer.name}: {e}")
                        error_count += 1

            messages.success(request, f"Interest successfully added for {success_count} customers.")
            if error_count:
                messages.warning(request, f"Failed to process {error_count} customers. Check server logs.")

        except Exception as e:
            messages.error(request, f"Invalid input: {e}")

        return redirect('saving_home')

    return render(request, 'saving_home.html')



# /saving/add/<int:member_id>/
@login_required(login_url='loginpage')
def saving_add(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    loan = Loan.objects.filter(customer=member, status='active').first()

    if request.method == 'POST':
        form = SavingAddForm(request.POST, member=member)
        if form.is_valid():
            try:
                user_saving = form.cleaned_data.get('saving') or Decimal('0.00')
                user_interest = form.cleaned_data.get('interest_paid') or Decimal('0.00')
                user_principal = form.cleaned_data.get('principal_paid') or Decimal('0.00')
                other_fee = form.cleaned_data.get('other_fee') or Decimal('0.00')
                payment_method = form.cleaned_data.get('payment_method')
                remarks = form.cleaned_data.get('remarks')
                date = timezone.now()

                # Defaults
                interest_to_apply = Decimal('0.00')
                principal_to_apply = Decimal('0.00')
                principal_excess = Decimal('0.00')
                interest_excess = Decimal('0.00')
                total_repayment = Decimal('0.00')

                loan_id = request.POST.get('loan_id')
                loan_obj = None

                if loan_id:
                    loan_obj = get_object_or_404(Loan, id=loan_id)
                    interest_due = loan_obj.interest_to_pay()
                    principal_due = loan_obj.remaining_principal
                    # Pay interest
                    interest_to_apply = min(user_interest, interest_due)
                    interest_excess = max(user_interest - interest_due, Decimal('0.00'))
                    # Add excess interest to principal input
                    total_principal_input = user_principal + interest_excess
                    # Apply principal
                    principal_to_apply = min(total_principal_input, principal_due)
                    principal_excess = max(total_principal_input - principal_due, Decimal('0.00'))
                    # Record repayment
                    if interest_to_apply > 0 or principal_to_apply > 0:
                        Repayment.objects.create(
                            loan=loan_obj,
                            repayment_date=date,
                            amount_paid=interest_to_apply + principal_to_apply,
                            principal_paid=principal_to_apply,
                            interest_paid=interest_to_apply
                        )

                        loan_obj.remaining_principal -= principal_to_apply
                        loan_obj.remaining_principal = max(loan_obj.remaining_principal, Decimal('0.00'))
                        loan_obj.update_status_based_on_principal()
                        loan_obj.save()
                    total_repayment = interest_to_apply + principal_to_apply
                # Create deposit entry
                if user_saving > 0:
                    Deposit.objects.create(
                        customer=member,
                        amount=user_saving,
                        payment_method=payment_method,
                        remarks=remarks,
                        date=date
                    )
                # Record other fee
                if other_fee > 0:
                    OtherFee.objects.create(
                        customer=member,
                        amount=other_fee,
                        remarks=remarks
                    )
                # Create transaction (calculate saving_balance correctly)
                total_amount = user_saving + user_interest + user_principal + other_fee
                saving_balance = user_saving + principal_excess  # This includes excess repayment NOT applied to loan
                Transaction.objects.create(
                    member=member,
                    amount=total_amount,
                    saving_balance=saving_balance,
                    other_fee=other_fee,
                    loan_repayment=principal_to_apply,
                    interest_paid=interest_to_apply,
                    payment_method=payment_method,
                    date=date,
                    remarks=remarks
                )
                messages.success(
                    request,
                    f"Saved: Saving = {user_saving}, Interest = {user_interest} (Applied: {interest_to_apply}), "
                    f"Principal = {user_principal} (+ Excess Interest {interest_excess}) → Applied: {principal_to_apply}, "
                    f"Other Fee = {other_fee}, Saving Balance Recorded = {saving_balance}"
                )
                return redirect('saving_home')
            except Exception as e:
                print("Error during saving:", e)
                messages.error(request, "An error occurred while saving.")
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = SavingAddForm(member=member)
    return render(request, 'saving_add.html', {'form': form, 'member': member, 'loan': loan})

