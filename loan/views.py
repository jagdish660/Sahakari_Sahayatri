from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from loan.models import Loan, Repayment
from decimal import Decimal
from django.contrib import messages
from datetime import date
from customer.models import Transaction
from saving.models import Deposit


@login_required(login_url='loginpage')
def loan_home(request):
    # Only get loans with status "active"
    active_loans = Loan.objects.select_related('customer').filter(status='active').order_by('-id')
    # Calculate totals from active loans
    total_deployed = sum(loan.amount for loan in active_loans)
    current_year = timezone.now().year
    deployed_current_year = sum(
        loan.amount for loan in active_loans if loan.start_date.year == current_year
    )
    deployed_previous_year = total_deployed - deployed_current_year
    # Pagination
    paginator = Paginator(active_loans, 10)  # Show 10 loans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'loans': page_obj,  # Loans on current page
        'page_obj': page_obj,
        'total_deployed': total_deployed,
        'deployed_current_year': deployed_current_year,
        'deployed_previous_year': deployed_previous_year,
    }
    return render(request, 'loan_home.html', context)


def loan_all(request):
    loans = Loan.objects.select_related('customer').all().order_by('-id')
     # Pagination
    paginator = Paginator(loans,10)  # Show 10 loans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'loans': loans,
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
    paginator = Paginator(repayments, 10)  # Show 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'loan': loan,
        'page_obj': page_obj,  # This contains the paginated repayment transactions
    }
    return render(request, 'loan_details.html', context)


# /loan/update/<int:id>


def loan_update(request, id):
    loan = get_object_or_404(Loan, id=id)

    if request.method == 'POST':
        try:
            interest_paid = Decimal(request.POST.get('interest_paid', '0'))
            principal_paid = Decimal(request.POST.get('principal_paid', '0'))
            remarks = request.POST.get('remarks', '')

            if interest_paid < 0 or principal_paid < 0:
                messages.error(request, "Interest and Principal paid must be non-negative.")
                return redirect('loan_update', id=loan.id)

            interest_to_pay = loan.interest_to_pay()
            remaining_principal = loan.remaining_principal

            # Interest logic
            applied_interest = min(interest_paid, interest_to_pay)
            excess_interest = max(interest_paid - interest_to_pay, Decimal('0.00'))

            # Total going toward principal
            total_principal_payment = principal_paid + excess_interest

            # Cap at remaining principal
            actual_principal_paid = min(total_principal_payment, remaining_principal)

            # Calculate new remaining principal
            new_remaining = remaining_principal - actual_principal_paid

            # Calculate any excess beyond loan
            total_payment = interest_paid + principal_paid
            used_payment = applied_interest + actual_principal_paid
            excess_for_deposit = max(total_payment - used_payment, Decimal('0.00'))

            # Save Repayment record
            repayment = Repayment.objects.create(
                loan=loan,
                previous_principal=remaining_principal,
                repayment_date=date.today(),
                amount_paid=total_payment,
                principal_paid=actual_principal_paid,
                interest_paid=applied_interest,
                remaining_principal=new_remaining.quantize(Decimal('0.01')),
                remarks=remarks
            )

            # Update loan principal and status
            loan.remaining_principal = new_remaining.quantize(Decimal('0.01'))
            loan.update_status_based_on_principal()
            loan.save()

            saved=excess_for_deposit.quantize(Decimal('0.01'))
            # Save excess deposit (if any)
            if excess_for_deposit > 0:
                Deposit.objects.create(
                    customer=loan.customer,
                    amount=saved,
                    date=date.today(),
                    payment_method='cash',
                    remarks=f"Excess payment deposit from loan #{loan.id}"
                )

            # Save Transaction
            Transaction.objects.create(
                member=loan.customer,
                date=date.today(),
                amount= interest_paid + principal_paid,
                loan_repayment=actual_principal_paid,
                interest_paid=applied_interest,
                other_fee=Decimal('0.00'),
                saving_balance=saved,
                remarks=f"Loan payment for Loan #{loan.id}",
                payment_method='cash'
            )

            messages.success(request, "Loan updated successfully.")
            return redirect('loan_details', id=loan.id)

        except Exception as e:
            print(e)
            messages.error(request, f"Error updating loan: {e}")
            return redirect('loan_update', id=loan.id)

    # GET request context
    if loan.customer.middle_name:
        name = f"{loan.customer.first_name} {loan.customer.middle_name} {loan.customer.last_name}"
    else:
        name = f"{loan.customer.first_name} {loan.customer.last_name}"

    context = {
        'loan': loan,
        'name': name,
    }
    return render(request, 'loan_update.html', context)

