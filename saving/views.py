from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from datetime import date
from share.models import ShareCapital
from customer.models import Member, Transaction
from loan.models import Loan, Repayment
from expenses.models import Expense, TotalExpense
from saving.models import Deposit, YearlyInterest, SavingRefund, SavingBalance, OtherFee, get_fiscal_year_starting_shrawan, get_fiscal_year_start_end
from saving.forms import SavingAddForm
from django.core.paginator import Paginator
from django.db.models import Sum, F
from decimal import Decimal, ROUND_HALF_UP
from loan.utils import interest_to_pay

# Create your views here.
def get_fiscal_year_start():
    today = date.today()
    if today.month > 7 or (today.month == 7 and today.day >= 16):  # Assuming Shrawan 1 is around July 16
        return date(today.year, 7, 16)
    else:
        return date(today.year - 1, 7, 16)



# /saving/
@login_required(login_url='loginpage')
def saving_home(request):
    if request.user.is_staff or request.user.is_superuser:
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
    else:
        return redirect('home')




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
    paginator = Paginator(detailed_transactions,25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'saving_details.html', {
        'member': member,
        'page_obj': page_obj,
        'transactions': detailed_transactions,
    })


# /saving/interest/ 
@login_required(login_url='loginpage')
def saving_interest(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            try:
                previous_rate = Decimal(request.POST.get('previous_rate'))
                current_rate = Decimal(request.POST.get('current_rate'))

                current_date = date.today()
                fiscal_year = get_fiscal_year_starting_shrawan(current_date)
                fiscal_year_start_date, fiscal_year_end_date = get_fiscal_year_start_end(fiscal_year)

                customers = Member.objects.all()
                success_count = 0
                error_count = 0

                for customer in customers:
                    if not YearlyInterest.objects.filter(customer=customer, year=fiscal_year).exists():
                        try:
                            # Sum of deposits BEFORE fiscal year start
                            prev_deposits = Deposit.objects.filter(
                                customer=customer,
                                date__lt=fiscal_year_start_date
                            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

                            # Sum of interest credited BEFORE fiscal year start
                            prev_interests = YearlyInterest.objects.filter(
                                customer=customer,
                                date__lt=fiscal_year_start_date
                            ).aggregate(
                                total=Sum(F('previous_interest_amount') + F('current_interest_amount'))
                            )['total'] or Decimal('0.00')

                            previous_saving = prev_deposits + prev_interests

                            # Sum of deposits DURING the fiscal year
                            curr_deposits = Deposit.objects.filter(
                                customer=customer,
                                date__gte=fiscal_year_start_date,
                                date__lte=fiscal_year_end_date
                            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

                            # Sum of interests DURING the fiscal year
                            curr_interests = YearlyInterest.objects.filter(
                                customer=customer,
                                date__gte=fiscal_year_start_date,
                                date__lte=fiscal_year_end_date
                            ).aggregate(
                                total=Sum(F('previous_interest_amount') + F('current_interest_amount'))
                            )['total'] or Decimal('0.00')

                            current_saving = curr_deposits + curr_interests

                            # Calculate interest
                            previous_interest = (previous_saving * previous_rate / Decimal('100')).quantize(Decimal('0.01'))
                            current_interest = (current_saving * current_rate / Decimal('100')).quantize(Decimal('0.01'))
                            interest_total = (previous_interest + current_interest).quantize(Decimal('0.01'))

                            # Update saving balance
                            balance_obj, _ = SavingBalance.objects.get_or_create(customer=customer)
                            balance_obj.balance += interest_total
                            balance_obj.save()

                            # Log
                            print(f"{fiscal_year}: {customer.name} - Prev Amt: {previous_saving}, Int: {previous_interest} ({previous_rate}%) | Curr Amt: {current_saving}, Int: {current_interest} ({current_rate}%)")

                            # Save YearlyInterest
                            YearlyInterest.objects.create(
                                customer=customer,
                                year=fiscal_year,
                                previous_interest_rate=previous_rate,
                                previous_interest_amount=previous_interest,
                                current_interest_rate=current_rate,
                                current_interest_amount=current_interest,
                                remarks=f"Interest for FY {fiscal_year}"
                            )

                            # Log Transaction
                            Transaction.objects.create(
                                date=timezone.now(),
                                member=customer,
                                amount=interest_total,
                                saving_balance=balance_obj.balance,  # Updated balance
                                loan_repayment=0,
                                interest_paid=interest_total,
                                share=0,
                                other_fee=0,
                                payment_method="interest",
                                remarks=f"Interest credited for FY {fiscal_year}",
                            )

                            success_count += 1

                        except Exception as e:
                            print(f"Error processing {customer.name}: {e}")
                            error_count += 1

                messages.success(request, f"Interest successfully added for {success_count} customers.")
                if error_count:
                    messages.warning(request, f"Failed to process {error_count} customers. Check server logs.")

            except Exception as e:
                messages.error(request, f"Invalid input: {e}")

            return redirect('saving_interest')

        return render(request, 'saving_yearly_interest.html')
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('saving_home')


# /saving/add/<int:member_id>/
@login_required(login_url='loginpage')
def saving_add(request, member_id):
    if request.user.is_staff or request.user.is_superuser:
            
        member = get_object_or_404(Member, member_id=member_id)
        loan = Loan.objects.filter(customer=member, status='active').first()
        if loan:
            interest_due = interest_to_pay(loan)
        if request.method == 'POST':
            form = SavingAddForm(request.POST, member=member)
            if form.is_valid():
                try:
                    # Form data
                    user_saving = form.cleaned_data.get('saving') or Decimal('0.00')
                    user_interest = form.cleaned_data.get('interest_paid') or Decimal('0.00')
                    user_principal = form.cleaned_data.get('principal_paid') or Decimal('0.00')
                    other_fee = form.cleaned_data.get('other_fee') or Decimal('0.00')
                    payment_method = form.cleaned_data.get('payment_method')
                    remarks = form.cleaned_data.get('remarks')
                    date_now = timezone.now()
                    if not user_saving:
                        messages.error(request, "You didn't entered saving amount.")
                        return redirect('saving_home')
                    interest_to_apply = Decimal('0.00')
                    principal_to_apply = Decimal('0.00')
                    interest_excess = Decimal('0.00')
                    principal_excess = Decimal('0.00')

                    loan_id = request.POST.get('loan_id')
                    loan_obj = None
                    total_repayment = Decimal('0.00')

                    if loan_id:
                        loan_obj = get_object_or_404(Loan, id=loan_id)
                        # interest_due = interest_to_pay(loan_obj)
                        principal_due = loan_obj.remaining_principal

                        print(f"User Interest: {user_interest}")
                        print(f"Interest Due: {interest_due}")

                        # Validation
                        if user_interest < interest_due:
                            messages.error(request, "You must pay at least the total interest due.")
                            return redirect('saving_home')

                        # Apply interest
                        interest_to_apply = min(user_interest, interest_due)
                        interest_excess = user_interest - interest_due

                        # Principal + any excess interest
                        total_principal_input = user_principal + interest_excess
                        principal_to_apply = min(total_principal_input, principal_due)
                        principal_excess = total_principal_input - principal_to_apply

                        print(f"Interest to Apply: {interest_to_apply}")
                        print(f"Interest Excess: {interest_excess}")
                        print(f"Principal to Apply: {principal_to_apply}")
                        print(f"Principal Excess: {principal_excess}")

                        if interest_to_apply > 0 or principal_to_apply > 0:
                            repayment = Repayment.objects.create(
                                loan=loan_obj,
                                repayment_date=date_now,
                                amount_paid=interest_to_apply + principal_to_apply,
                                interest_paid=interest_to_apply,
                                principal_paid=principal_to_apply,
                                previous_principal=loan_obj.remaining_principal,
                                remarks=remarks,
                                remaining_principal=principal_excess,
                            )
                            total_repayment = repayment.amount_paid

                    # Saving Deposit
                    if user_saving > 0:
                        Deposit.objects.create(
                            customer=member,
                            amount=user_saving,
                            payment_method=payment_method,
                            remarks=remarks,
                            date=date_now
                        )

                    # Other Fees
                    if other_fee > 0:
                        OtherFee.objects.create(
                            customer=member,
                            amount=other_fee,
                            remarks=remarks
                        )

                    # Transaction
                    total_amount = user_saving + user_interest + user_principal + other_fee
                    saving_balance = user_saving + principal_excess

                    Transaction.objects.create(
                        member=member,
                        amount=total_amount,
                        saving_balance=saving_balance,
                        other_fee=other_fee,
                        loan_repayment=principal_to_apply,
                        interest_paid=interest_to_apply,
                        payment_method=payment_method,
                        date=date_now,
                        remarks=remarks
                    )
                    if total_repayment == 0:
                        messages.success(request, f"Saving: Rs. {user_saving} added successfully.")
                        return redirect('saving_home')
                    else:
                        messages.success(request,
                            f"Saving: ₹{user_saving}\n"
                            f"- Interest Paid: Rs. {interest_to_apply}\n"
                            f"- Principal Paid: Rs. {principal_to_apply}\n"
                        )
                        return redirect('saving_home')

                except Exception as e:
                    print("Error during saving:", e)
                    messages.error(request, "An error occurred while processing the saving.")
            else:
                messages.error(request, "Invalid form data submitted.")
        else:
            form = SavingAddForm(member=member)
        if loan:
            return render(request, 'saving_add.html', {'form': form, 'member': member, 'loan': loan, 'interest_to_pay': interest_due})
        else:
            return render(request, 'saving_add.html', {'form': form, 'member': member, 'loan': loan})
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('saving_home')



