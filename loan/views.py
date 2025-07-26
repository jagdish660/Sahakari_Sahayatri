from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from loan.models import Loan, Repayment
from share.models import ShareBalance, ShareCapital, ShareRefund
from customer.models import Member
from expenses.models import Expense, TotalExpense
from decimal import Decimal
from django.contrib import messages
from datetime import date
from customer.models import Transaction
from saving.models import Deposit, YearlyInterest
from loan.utils import interest_to_pay
from collections import defaultdict
from django.utils.timezone import now

def get_balance_now():
    loans = Loan.objects.select_related('customer').all().order_by('-id')
    savings = Deposit.objects.select_related('customer').all().order_by('-date')
    interest = YearlyInterest.objects.all().order_by('-date')
    expenses = Expense.objects.all().order_by('-date')
    share_balances = ShareCapital.objects.select_related('customer').all().order_by('-id')

    total_deployed = sum(loan.amount for loan in loans)
    remaining_principal = sum(loan.remaining_principal for loan in loans if loan.status == 'active')
    total_interest = sum(i.previous_interest_amount + i.current_interest_amount for i in interest)
    total_expenses_amount = sum(e.amount for e in expenses)
    total_expenses = total_expenses_amount + total_interest
    total_savings = sum(d.amount for d in savings) + total_interest
    total_shares = sum(s.share_amount for s in share_balances)
    principal_paid = total_deployed - remaining_principal
    balance_now = total_savings - remaining_principal + total_shares - total_expenses
    return balance_now

@login_required(login_url='loginpage')
def loan_home(request):
    if request.user.is_staff or request.user.is_superuser:
        active_loans = Loan.objects.select_related('customer').filter(status='active').order_by('-id')
        
        total_deployed = sum(loan.amount for loan in active_loans)

        today = date.today()
        fiscal_year_start = date(today.year, 7, 16)  # Shrawan 1 approx in Gregorian

        # If today's date is before Shrawan 1, then the fiscal year started last year
        if today < fiscal_year_start:
            fiscal_year_start = date(today.year - 1, 7, 16)

        deployed_current_fiscal_year = sum(
            loan.amount for loan in active_loans if loan.start_date >= fiscal_year_start
        )

        deployed_previous_year = total_deployed - deployed_current_fiscal_year

        paginator = Paginator(active_loans, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'loans': page_obj,
            'page_obj': page_obj,
            'total_deployed': total_deployed,
            'deployed_current_year': deployed_current_fiscal_year,
            'deployed_previous_year': deployed_previous_year,
        }
        return render(request, 'loan_home.html', context)
    else:
        return redirect('loan_all')


# /loan/all/
@login_required(login_url='loginpage')
def loan_all(request):
    if request.user.is_staff or request.user.is_superuser:
        loans = Loan.objects.select_related('customer').all().order_by('-start_date')
        paginator = Paginator(loans, 5)
    else:
        try:
            member = Member.objects.get(email=request.user.email)
            loans = Loan.objects.select_related('customer').filter(customer=member).order_by('-start_date')
            paginator = Paginator(loans, 10)
        except Member.DoesNotExist:
            messages.error(request, "Member profile not found.")
            return redirect('home')
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'loans': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'loan_all.html', context)


# /# loan/<int:id>/
@login_required(login_url='loginpage')
def loan_details(request, id):
    loan = get_object_or_404(Loan.objects.select_related('customer'), id=id)

    # Get all repayments for the loan, ordered by repayment date
    repayments = loan.repayments.all().order_by('repayment_date')

    # Paginate repayments
    paginator = Paginator(repayments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'loan': loan,
        'page_obj': page_obj,  # This contains the paginated repayment transactions
    }
    return render(request, 'loan_details.html', context)


# /loan/update/<int:id>/
@login_required(login_url='loginpage')
def loan_update(request, id):
    if request.user.is_staff or request.user.is_superuser:
        loan = get_object_or_404(Loan, id=id)
        # Always calculate this for both GET and POST
        interest_due = interest_to_pay(loan)
        if request.method == 'POST':
            try:
                interest_paid = Decimal(request.POST.get('interest_paid', '0'))
                principal_paid = Decimal(request.POST.get('principal_paid', '0'))
                remarks = request.POST.get('remarks', '').strip()
                if interest_paid < 0:
                    messages.error(request, "Interest paid must not be zero or negative.")
                    return redirect('loan_update', id=loan.id)
                if principal_paid < 0:
                    messages.error(request, "Principal paid must not be zero or negative.")
                    return redirect('loan_update', id=loan.id)
                if interest_paid < interest_due:
                    messages.error(request, "You're not allowed to pay interest less than interest due.")
                    return redirect('loan_update', id=loan.id)
                remaining_principal = loan.remaining_principal
                # Apply interest payment
                applied_interest = min(interest_paid, interest_due)
                excess_interest = max(interest_paid - applied_interest, Decimal('0.00'))
                # Apply principal payment (including any excess from interest)
                total_principal_payment = principal_paid + excess_interest
                actual_principal_paid = min(total_principal_payment, remaining_principal)
                new_remaining = (remaining_principal - actual_principal_paid).quantize(Decimal('0.01'))
                # Check for total overpayment
                total_payment = interest_paid + principal_paid
                used_payment = applied_interest + actual_principal_paid
                excess_for_deposit = max(total_payment - used_payment, Decimal('0.00')).quantize(Decimal('0.01'))
                # Save Repayment record
                Repayment.objects.create(
                    loan=loan,
                    previous_principal=remaining_principal,
                    repayment_date=date.today(),
                    amount_paid=total_payment,
                    principal_paid=actual_principal_paid,
                    interest_paid=applied_interest,
                    remaining_principal=new_remaining,
                    remarks=remarks
                )
                # Update loan balance
                loan.remaining_principal = new_remaining
                loan.update_status_based_on_principal()
                loan.save()
                # Handle excess deposit
                if excess_for_deposit > 0:
                    Deposit.objects.create(
                        customer=loan.customer,
                        amount=excess_for_deposit,
                        date=date.today(),
                        payment_method='cash',
                        remarks=f"Excess payment deposit from Loan #{loan.id}"
                    )
                # Log transaction
                Transaction.objects.create(
                    member=loan.customer,
                    date=date.today(),
                    amount=total_payment,
                    loan_repayment=actual_principal_paid,
                    interest_paid=applied_interest,
                    other_fee=Decimal('0.00'),
                    saving_balance=excess_for_deposit,
                    remarks=f"Loan payment for Loan #{loan.id}",
                    payment_method='cash'
                )
                messages.success(request, "Loan updated successfully.")
                return redirect('loan_home' if request.user.is_staff or request.user.is_superuser else 'about_me')
            except Exception as e:
                print(f"Loan update error: {e}")
                messages.error(request, f"Error updating loan: {str(e)}")
                return redirect('loan_update', id=loan.id)
        # GET: show form with interest_due
        context = {
            'loan': loan,
            'interest_due': interest_due,
        }
        return render(request, 'loan_update.html', context)
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('loan_home')


# /loan/all/<int:id>/
@login_required(login_url='loginpage')
def user_loan_all(request, id):
    try:
        member = Member.objects.get(member_id=id)
        loans = Loan.objects.select_related('customer').filter(customer=member).order_by('-start_date')
    except Member.DoesNotExist:
        messages.error(request, "Member profile not found.")
        return redirect('home')
    paginator = Paginator(loans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'loans': loans,
        'page_obj': page_obj,
        'member':member,
    }
    return render(request, 'user_loan_all.html', context)


# /loan/add/
@login_required(login_url='loginpage')
def loan_add(request):
    members = Member.objects.all()
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            customer_id = request.POST.get('customer_id')
            principal = request.POST.get('principal')
            rate = request.POST.get('rate')
            if not customer_id:
                messages.error(request, "Please select a valid customer.")
                return render(request, 'loan_add.html', {'members': members})
            try:
                balance_now=get_balance_now()
                if Decimal(principal) > balance_now:
                    messages.error(request, "You don't have enough balance to provide loan")
                    return redirect('loan_home')
                customer = Member.objects.get(pk=int(customer_id))
                if Loan.objects.filter(customer=customer, status='active').exists():
                    messages.error(request, f"{customer.name} already has an active loan.")
                    return render(request, 'loan_add.html', {'members': members})
                Loan.objects.create(
                    customer=customer,
                    amount=Decimal(principal),
                    interest_rate=Decimal(rate),
                    start_date=timezone.now()
                )
                messages.success(request, f"Loan successfully deployed to {customer.name}.")
                return redirect('loan_home')
            except Member.DoesNotExist:
                messages.error(request, "Selected customer not found.")
            except Exception as e:
                messages.error(request, f"Unexpected Error: {e}")
        return render(request, 'loan_add.html', {'members': members})
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('home')

 # Assuming balance is based on transactions


# /loan/add/<int:id>/
@login_required(login_url='loginpage')
def loan_add_individual(request, id):
    member = get_object_or_404(Member, member_id=id)
    
    if (request.user.is_staff or request.user.is_superuser):
        if request.method == 'POST':
            principal = request.POST.get('principal')
            rate = request.POST.get('rate')

            try:
                balance_now=get_balance_now()
                if Decimal(principal) > balance_now:
                    print(balance_now)
                    messages.error(request, "You don't have enough balance to provide loan")
                    return redirect('loan_home')
                # Check for active loan
                if Loan.objects.filter(customer=member, status='active').exists():
                    messages.error(request, f"{member.name} already has an active loan.")
                    return render(request, 'loan_add_individual.html', {'member': member})

                # Deploy loan
                Loan.objects.create(
                    customer=member,
                    amount=Decimal(principal),
                    interest_rate=Decimal(rate),
                    start_date=timezone.now()
                )
                messages.success(request, f"Loan successfully deployed to {member.name}.")
                return redirect('customer_details', member.member_id)

            except Exception as e:
                messages.error(request, f"Unexpected Error: {e}")

        return render(request, 'loan_add_individual.html', {'member': member})
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('loan_home')

