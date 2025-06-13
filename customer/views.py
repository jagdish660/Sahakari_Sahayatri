from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from customer.models import Member
from saving.models import SavingBalance, Deposit, SavingRefund, YearlyInterest
from loan.models import Loan, Repayment
from share.models import ShareCapital, ShareRefund
from customer.forms import MemberForm, UpdateMemberForm
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

# Create your views here.
def member_home(request):
    customers = Member.objects.all()
    return render(request, 'customer_home.html', {'customers': customers})



def member_details(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)

    # Fetch savings data
    deposits = Deposit.objects.filter(customer=member)
    refunds = SavingRefund.objects.filter(customer=member)
    interests = YearlyInterest.objects.filter(customer=member)

    # Prepare saving transactions
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
            'amount': total_interest,
            'payment_method': 'Auto',
            'remarks': f"Interest for FY {interest.year}",
        })

    # Sort saving transactions (newest first)
    transactions.sort(key=lambda x: x['date'], reverse=True)

    METHOD_DISPLAY = {
        'cash': 'Cash',
        'bank_transfer': 'Bank Transfer',
        'cheque': 'Cheque',
        'Auto': 'Interest',
    }

    running_balance = 0
    detailed_transactions = []
    for tx in reversed(transactions):  # accumulate from oldest
        previous_balance = running_balance
        running_balance += tx['amount']
        detailed_transactions.append({
            'member_id': member_id,
            'date': tx['date'],
            'type': tx['type'],
            'amount': abs(tx['amount']),
            'previous_balance': previous_balance,
            'balance': running_balance,
            'payment_method': METHOD_DISPLAY.get(tx['payment_method'], tx['payment_method']),
            'remarks': tx['remarks'],
        })
    detailed_transactions.reverse()

    # === Loan Transactions ===
    loans = Loan.objects.filter(customer=member).order_by('start_date')  # newest first
    loan_transactions = []
    for loan in loans:
        loan_transactions.append({
            'date': loan.start_date,
            'amount': loan.amount,
            'interest_rate': loan.interest_rate, 
            'remaining_principal': loan.remaining_principal,
            'last_renewed': loan.last_renewed,
        })

    # === Share Transactions ===
    shares = ShareCapital.objects.filter(customer=member).order_by('purchase_date')  # newest first
    share_transactions = []
    for share in shares:
        share_transactions.append({
            'date': share.purchase_date,
            'amount': share.share_amount
        })

    return render(request, 'customer_details.html', {
        'member': member,
        'transactions': detailed_transactions,
        'loan_transactions': loan_transactions,
        'share_transactions': share_transactions,
    })


def member_add(request):
    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        citizenship_number = request.POST.get('citizenship_number')
        date_of_birth = request.POST.get('date_of_birth')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        occupation = request.POST.get('occupation')
        # Validate required fields
        if not all([member_id, first_name, last_name, address, date_of_birth, citizenship_number, phone_number]):
            messages.error(request, "Please! Fill all the required fields.")
            return redirect('customer_add')
        # Check uniqueness
        if Member.objects.filter(member_id=member_id).exists():
            messages.error(request, "Member with this ID already exists.")
            return redirect('customer_add')
        if Member.objects.filter(citizenship_number=citizenship_number).exists():
            messages.error(request, "Member with this citizenship number already exists.")
            return redirect('customer_add')
        if email and Member.objects.filter(email=email).exists():
            messages.error(request, "This email is already in use.")
            return redirect('customer_add')
        if Member.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "This phone number is already in use.")
            return redirect('customer_add')
        # Save the new member
        try:
            member = Member(
                member_id=member_id,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                address=address,
                citizenship_number=citizenship_number,
                occupation=occupation,
            )
            member.save()
            messages.success(request, "Member added successfully!")
            return redirect('customer_home')
        except IntegrityError:
            messages.error(request, "A database error occurred. Please try again later.")
            return render(request, 'customer_add.html', {'form': MemberForm()})
        except Exception as e:
            messages.error(request, f"There was an error adding the member.")
            return render(request, 'customer_add.html', {'form': MemberForm()})
    else:
        form = MemberForm()
        return render(request, 'customer_add.html', {'form': form})


def update_member(request, id):
    member = get_object_or_404(Member, member_id=id)
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        date_of_birth = request.POST.get('date_of_birth')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        occupation = request.POST.get('occupation')
        # Validate required fields
        if not all([first_name, last_name, date_of_birth, address, phone_number]):
            messages.error(request, "Please! Fill all the required fields.")
            return render(request, 'customer_update.html', {'form': member, 'id': id})
        if email and Member.objects.filter(email=email).exclude(member_id=id).exists():
            messages.error(request, "This email is already in use.")
            return render(request, 'customer_update.html', {'form': member, 'id': id})
        if Member.objects.filter(phone_number=phone_number).exclude(member_id=id).exists():
            messages.error(request, "This phone number is already in use.")
            return render(request, 'customer_update.html', {'form': member, 'id': id})
        try:
            member.first_name = first_name
            member.middle_name = middle_name
            member.last_name = last_name
            member.date_of_birth = date_of_birth
            member.address = address
            member.phone_number = phone_number
            member.email = email
            member.occupation = occupation
            member.save()
            messages.success(request, "Member updated successfully!")
            return redirect('customer_home')
        except IntegrityError:
            messages.error(request, "A database error occurred. Please try again later.")
            return render(request, 'customer_update.html', {'form': member, 'id': id})
        except Exception:
            messages.error(request, "There was an error updating the member.")
            return render(request, 'customer_update.html', {'form': member, 'id': id})
    # For GET request just display form with current member data
    return render(request, 'customer_update.html', {'form': member, 'id': id})
