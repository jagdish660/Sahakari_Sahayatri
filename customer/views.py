from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.db import IntegrityError
from django.core.paginator import Paginator
from customer.models import Member, Transaction
from saving.models import SavingBalance, Deposit, SavingRefund, YearlyInterest
from loan.models import Loan, Repayment
from share.models import ShareCapital, ShareRefund
from customer.forms import MemberForm
import secrets
import string
from decimal import Decimal
import re
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.conf import settings


#  /member
@login_required(login_url='loginpage')
def member_home(request ):
    if request.user.is_staff or request.user.is_superuser:
        customers = Member.objects.all()
        return render(request, 'customer_home.html', {'customers': customers})
    else:
        messages.error(request, "You're not allowed to enter this page.")
    


#  /member/details/<int:member_id>
@login_required(login_url='loginpage')
def member_details(request, member_id):
    if request.user.is_staff or request.user.is_superuser:
        member = get_object_or_404(Member, member_id=member_id)
        name = f"{member.first_name} {member.middle_name + ' ' if member.middle_name else ''}{member.last_name}"
        # Fetch savings data
        deposits = Deposit.objects.filter(customer=member)
        refunds = SavingRefund.objects.filter(customer=member)
        interests = YearlyInterest.objects.filter(customer=member)
        # Prepare saving transactions
        transactions = []
        total_deposit = Decimal('0.00')
        total_refund = Decimal('0.00')
        total_interest_gain = Decimal('0.00')
        for deposit in deposits:
            total_deposit += deposit.amount
            transactions.append({
                'date': deposit.date,
                'type': 'Deposit',
                'amount': deposit.amount,
                'payment_method': deposit.payment_method,
                'remarks': deposit.remarks,
            })
        for refund in refunds:
            total_refund += refund.amount_refunded
            transactions.append({
                'date': refund.refund_date,
                'type': 'Refund',
                'amount': -refund.amount_refunded,
                'payment_method': refund.payment_method,
                'remarks': refund.remarks,
            })
        for interest in interests:
            interest_amount = interest.previous_interest_amount + interest.current_interest_amount
            total_interest_gain += interest_amount
            transactions.append({
                'date': interest.date,
                'type': 'Interest',
                'amount': interest_amount,
                'payment_method': 'Auto',
                'remarks': f"Interest for FY {interest.year}",
            })
        total_saved = total_deposit + total_interest_gain - total_refund
        transactions.sort(key=lambda x: x['date'], reverse=True)    # Sort saving transactions (newest first)

        METHOD_DISPLAY = {
            'cash': 'Cash',
            'bank_transfer': 'Bank Transfer',
            'cheque': 'Cheque',
            'Auto': 'Interest',
        }
        running_balance = Decimal('0.00')
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
        loans = Loan.objects.filter(customer=member).order_by('start_date')
        loan_transactions = [{
            'id': loan.id,
            'date': loan.start_date,
            'amount': loan.amount,
            'interest_rate': loan.interest_rate,
            'remaining_principal': loan.remaining_principal,
            'last_renewed': loan.last_renewed,
            'status': loan.status
        } for loan in loans]
        # === Share Transactions ===
        share_purchases = ShareCapital.objects.filter(customer=member)
        share_refunds = ShareRefund.objects.filter(customer=member)
        share_events = []

        # Combine purchases and refunds
        for share in share_purchases:
            share_events.append({
                'date': share.purchase_date,
                'amount': Decimal(share.share_amount),
                'type': 'Purchase',
                'remarks': getattr(share, 'remarks', '')
            })

        for refund in share_refunds:
            share_events.append({
                'date': refund.refund_date,
                'amount': Decimal(-refund.refund_amount),  # refund reduces balance
                'type': 'Refund',
                'remarks': f"Refunded {refund.refund_amount} shares"
            })

        # Sort by date
        share_events.sort(key=lambda x: x['date'])

        total_share = Decimal('0.00')
        running_share = Decimal('0.00')
        share_transactions = []

        for event in share_events:
            previous_share = running_share
            running_share += event['amount']
            share_transactions.append({
                'date': event['date'],
                'type': event['type'],
                'amount': abs(event['amount']),
                'previous_share': previous_share,
                'balance': running_share,
                'remarks': event['remarks'],
            })

        total_share = running_share 

        paginator = Paginator(detailed_transactions, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'customer_details.html', {
            'member': member,
            'name': name,
            'total_share': total_share,
            'total_saved': total_saved,
            'transactions': detailed_transactions,
            'loan_transactions': loan_transactions,
            'share_transactions': share_transactions,
            'page_obj': page_obj
        })
    else:
        return redirect('about_me')


@login_required(login_url='loginpage')
def about_me(request):
    member = get_object_or_404(Member, user=request.user)
    # Fetch savings data
    deposits = Deposit.objects.filter(customer=member)
    refunds = SavingRefund.objects.filter(customer=member)
    interests = YearlyInterest.objects.filter(customer=member)
    # Prepare saving transactions
    transactions = []
    total_deposit = Decimal('0.00')
    total_refund = Decimal('0.00')
    total_interest_gain = Decimal('0.00')
    for deposit in deposits:
        total_deposit += deposit.amount
        transactions.append({
            'date': deposit.date,
            'type': 'Deposit',
            'amount': deposit.amount,
            'payment_method': deposit.payment_method,
            'remarks': deposit.remarks,
        })
    for refund in refunds:
        total_refund += refund.amount_refunded
        transactions.append({
            'date': refund.refund_date,
            'type': 'Refund',
            'amount': -refund.amount_refunded,
            'payment_method': refund.payment_method,
            'remarks': refund.remarks,
        })
    for interest in interests:
        interest_amount = interest.previous_interest_amount + interest.current_interest_amount
        total_interest_gain += interest_amount
        transactions.append({
            'date': interest.date,
            'type': 'Interest',
            'amount': interest_amount,
            'payment_method': 'Auto',
            'remarks': f"Interest for FY {interest.year}",
        })
    total_saved = total_deposit + total_interest_gain - total_refund
    transactions.sort(key=lambda x: x['date'], reverse=True)    # Sort saving transactions (newest first)

    METHOD_DISPLAY = {
        'cash': 'Cash',
        'bank_transfer': 'Bank Transfer',
        'cheque': 'Cheque',
        'Auto': 'Interest',
    }
    running_balance = Decimal('0.00')
    detailed_transactions = []
    for tx in reversed(transactions):  # accumulate from oldest
        previous_balance = running_balance
        running_balance += tx['amount']
        detailed_transactions.append({
            'member_id': member.member_id,
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
    loans = Loan.objects.filter(customer=member).order_by('start_date')
    loan_transactions = [{
        'id': loan.id,
        'date': loan.start_date,
        'amount': loan.amount,
        'interest_rate': loan.interest_rate,
        'remaining_principal': loan.remaining_principal,
        'last_renewed': loan.last_renewed,
        'status': loan.status
    } for loan in loans]
    # === Share Transactions ===
    shares = ShareCapital.objects.filter(customer=member).order_by('purchase_date')
    share_transactions = []
    total_share = Decimal('0.00')
    for share in shares:
        total_share += share.share_amount
        share_transactions.append({
            'date': share.purchase_date,
            'amount': share.share_amount
        })
    paginator = Paginator(detailed_transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'about_me.html', {
        'member': member,
        'total_share': total_share,
        'total_saved': total_saved,
        'transactions': detailed_transactions,
        'loan_transactions': loan_transactions,
        'share_transactions': share_transactions,
        'page_obj': page_obj
    })



# /member/add
@login_required(login_url='loginpage')
def member_add(request):
    if request.user.is_staff or request.user.is_superuser:
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

            if not all([member_id, first_name, last_name, address, date_of_birth, citizenship_number, phone_number]):
                messages.error(request, "Please! Fill all the required fields.")
                return redirect('customer_add')
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
            if email and User.objects.filter(username=email).exists():
                messages.error(request, "A user with this email already exists.")
                return redirect('customer_add')
            try:
                # Create the User FIRST
                full_first_name = f"{first_name} {middle_name}" if middle_name else first_name
                username = f"{first_name.lower()}_{member_id}"
                alphabet = string.ascii_letters + string.digits + ".@#$%&"
                password = ''.join(secrets.choice(alphabet) for _ in range(8))

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=full_first_name,
                    last_name=last_name,
                    password=password,
                    is_staff=False,
                    is_superuser=False,
                    is_active=True
                )
                user.save()
                # Now create the Member and associate the User
                member = Member(
                    user=user,
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
                # Send email with credentials
                subject = f'Account Created for {full_first_name} {last_name} - Sahakari Sahayatri'
                message = f"""
                    <html>
                    <body>
                        <p>Hello <strong><em>{full_first_name} {last_name}</em></strong>,</p>

                        <p>Welcome to <strong>Sahakari Sahayatri App</strong>! Your account has been successfully created.</p>

                        <p>Here are your login credentials:</p>
                        <ul>
                            <li><strong>Member ID:</strong> "{member_id}"</li>
                            <li><strong>Username:</strong> "{username}"</li>
                            <li><strong>Password:</strong> "{password}"</li>
                        </ul>

                        <p>Please log in using the above credentials. For security reasons, we recommend changing your password after your first login.</p>

                        <p>If you did not request this account, please contact our support team immediately.</p>

                        <br>
                        <p>Best Regards,</p>
                        <p><strong>Sahakari Sahayatri App Team</strong></p>
                    </body>
                    </html>
                """
                from_email = f"Sahakari Sahayatri App <{settings.EMAIL_HOST_USER}>"
                send_mail(
                    subject,
                    "",
                    from_email,
                    [email],
                    fail_silently=False,
                    html_message=message
                )
                messages.success(request, f"Member account created successfully with username: '{username}'!")
                return redirect('customer_home')
            except IntegrityError as e:
                print(e)
                messages.error(request, "A database error occurred. Please try again later.")
                return render(request, 'customer_add.html', {'form': MemberForm()})
            except Exception as e:
                messages.error(request, f"There was an error adding the member: {str(e)}")
                return render(request, 'customer_add.html', {'form': MemberForm()})
        else:
            form = MemberForm()
            return render(request, 'customer_add.html', {'form': form})
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('home')


# /member/update/<int:id>
@login_required(login_url='loginpage')
def update_customer(request, id):
    if request.user.is_staff or request.user.is_superuser:
        member = get_object_or_404(Member, member_id=id)
        user = User.objects.filter(username__endswith=f"_{member.member_id}").first()
        if request.method == 'POST':
            first_name = request.POST.get('first_name')
            middle_name = request.POST.get('middle_name')
            last_name = request.POST.get('last_name')
            date_of_birth = request.POST.get('date_of_birth')
            address = request.POST.get('address')
            phone_number = request.POST.get('phone_number')
            email = request.POST.get('email')
            occupation = request.POST.get('occupation')
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
                if user:
                    user.first_name = f"{first_name} {middle_name}" if middle_name else first_name
                    user.last_name = last_name
                    user.email = email
                    user.save()
                messages.success(request, "Member updated successfully!")
                return redirect('customer_home')
            except IntegrityError:
                messages.error(request, "A database error occurred. Please try again later.")
            except Exception:
                messages.error(request, "There was an error updating the member.")
        else:
            form = MemberForm(instance=member)
        return render(request, 'customer_update.html', {'form': member, 'id': id})
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('home')


#  /member/details/update/<int:id>
@login_required(login_url='loginpage')
def user_update_customer(request, id):
    if not request.user.is_staff or request.user.is_superuser:
        member = get_object_or_404(Member, member_id=id)
        user = User.objects.filter(username__endswith=f"_{member.member_id}").first()
        if request.method == 'POST':
            address = request.POST.get('address')
            phone_number = request.POST.get('phone_number')
            email = request.POST.get('email')
            occupation = request.POST.get('occupation')
            if not all([address, phone_number]):
                messages.error(request, "Please fill all the required fields.")
                return render(request, 'user_customer_update.html', {'form': member, 'id': id})
            if email and Member.objects.filter(email=email).exclude(member_id=id).exists():
                messages.error(request, "This email is already in use.")
                return render(request, 'user_customer_update.html', {'form': member, 'id': id})
            if Member.objects.filter(phone_number=phone_number).exclude(member_id=id).exists():
                messages.error(request, "This phone number is already in use.")
                return render(request, 'user_customer_update.html', {'form': member, 'id': id})
            try:
                member.address = address
                member.phone_number = phone_number
                member.email = email
                member.occupation = occupation
                member.save()
                if user:
                    user.email = email
                    user.save()
                messages.success(request, "Your data was updated successfully!")
                return redirect('about_me')
            except IntegrityError:
                messages.error(request, "A database error occurred. Please try again later.")
            except Exception as e:
                messages.error(request, "There was an error updating the member.")
                print(e)
        return render(request, 'user_customer_update.html', {'form': member, 'id': id})
    else:
        messages.error(request, "This page accessible to member only")
        return redirect('customer_home')


# /member/details/delete/<int:id>
@login_required(login_url='loginpage')
def delete_customer(request, id):
    if request.user.is_staff or request.user.is_superuser:
        member = get_object_or_404(Member, member_id=id)
        user = User.objects.filter(username__endswith=f"_{member.member_id}").first()
        if request.method == 'POST':
            try:
                if user:
                    user.delete()
                member.delete()
                messages.success(request, "Member and user account deleted successfully!")
            except IntegrityError:
                messages.error(request, "This member cannot be deleted due to existing dependencies.")
            except Exception:
                messages.error(request, "There was an error deleting the member.")
        return redirect('customer_home')
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('home')


# /login
def loginpage(request):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "You have successfully logged in.")
                if request.user.is_staff or request.user.is_superuser:
                    return redirect('transactions')
                else:
                    return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('customer_home')
        else:
            return redirect('home')
    return render(request, 'login.html')


# /logout
@login_required(login_url='loginpage')
def logout_user(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have successfully logged out.")
    return redirect('loginpage')


# /member/change_password
@login_required(login_url='loginpage')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            messages.error(request, "Please fill all the required fields.")
            return render(request, 'change_password.html')

        if new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
            return render(request, 'change_password.html')

        user = authenticate(request, username=request.user.username, password=current_password)
        if user is not None:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Your password has been changed successfully.")
            return redirect('loginpage')
        else:
            messages.error(request, "Current password is incorrect.")
    
    return render(request, 'change_password.html')


# /reset_password/
def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Please provide an email address.")
            return redirect('reset_password')
        try:
            user = User.objects.get(email=email)
            username = user.username
            first_name = user.first_name if user.first_name else "User"
            last_name = user.last_name if user.last_name else "User"
            full_name = f'{first_name} {last_name}'
            # name = User.object.get(username=user)
        except User.DoesNotExist:
            messages.error(request, "No user found with that email address.")
            return redirect('reset_password')
        # Generate a verification code
        verification_code = get_random_string(length=6, allowed_chars='1234567890')
        # Store verification code and email in session
        request.session['verification_code'] = verification_code
        request.session['email'] = email
        # Send email with verification code
        subject = f'Password Reset Verification Code - Sahakari Sahayatri'
        message = f"""
            <html>
            <body>
                <p>Hello <strong><em>{full_name}</em></strong>,</p>
                <p>We received a request to reset your password for your account on <strong>Sahakari Sahayatri App</strong>.</p>
                <p>Your verification code is: <strong><em>{verification_code}</em></strong></p>
                <p>Please enter this code on the verification page to proceed with resetting your password.</p>
                <p>If you did not request a password reset, please ignore this email. Your account security is important to us.</p>
                <br>
                <p>Best Regards,</p>
                <p><strong>Sahakari Sahayatri App Team</strong></p>
            </body>
            </html>
            """
        from_email = f"Sahakari Sahayatri App <{settings.EMAIL_HOST_USER}>"
        # send_mail(subject, message, from_email, [email])
        send_mail(
            subject,
            "",
            from_email,
            [email],
            fail_silently=False,
            html_message=message  # Sends HTML-formatted email
        )
        messages.success(request, "A verification code has been sent to your email.")
        return redirect('verify_code')
    return render(request, 'reset_password.html')


#  /verify_code
def verify_code(request):
    if request.method == "POST":
        # Check if the user clicked "Resend Code"
        if "resend_code" in request.POST:
            email = request.session.get("email")
            if not email:
                messages.error(request, "Session expired. Please request a new password reset.")
                return redirect("reset_password")
            try:
                user = User.objects.get(email=email)
                username = user.username
                full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else "User"
            except User.DoesNotExist:
                messages.error(request, "User not found. Please try again.")
                return redirect("reset_password")
            # Generate a new verification code
            new_verification_code = get_random_string(length=6, allowed_chars="1234567890")
            request.session["verification_code"] = new_verification_code
            # Send the verification email again
            subject = f"New Verification Code - Sahakari Sahayatri App"
            message = f"""
            Hello {full_name},

            A new verification code has been generated for your password reset.

            Your new verification code is: {new_verification_code}

            Please enter this code on the verification page to proceed.

            If you did not request this, you can ignore this message.

            Best Regards,  
            Sahakari Sahayatri App Team
            """
            from_email = f"Sahakari Sahayatri App Team <{settings.EMAIL_HOST_USER}>"
            
            send_mail(subject, message, from_email, [email])

            messages.success(request, "A new verification code has been sent to your email.")
            return redirect("verify_code")  # Stay on the same page
        # Handle normal verification process (check entered code)
        entered_code = request.POST.get("code")
        stored_code = request.session.get("verification_code")

        if entered_code and entered_code == stored_code:
            messages.success(request, "Verification successful! You can now reset your password.")
            return redirect("reset_password_form")  # Redirect to the next step
        else:
            messages.error(request, "Invalid verification code. Please try again.")
            return redirect("verify_code")  # Stay on the page
    return render(request, "verify_code.html")


#  /reset_password_form
def reset_password_form(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, "Session expired. Please request a new verification code.")
        return redirect('reset_password')
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match. Please try again.")
            return redirect('reset_password_form')
        if len(new_password) < 8:  # Ensure password is at least 8 characters
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('reset_password_form')
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        # Clear the session after successful password reset
        del request.session['email']
        messages.success(request, "Your password has been reset successfully.")
        return redirect('loginpage')
    return render(request, 'reset_password_form.html')


