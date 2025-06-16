from django import forms
from django.utils.timezone import now
from loan.models import Loan
from customer.models import Member
from decimal import Decimal

class SavingAddForm(forms.Form):
    remarks = forms.CharField(required=False)
    # Read-only Member Info
    member_id = forms.CharField(label='Member ID', required=False, disabled=True)
    member_name = forms.CharField(label='Name', required=False, disabled=True)

    # Saving deposit
    saving = forms.DecimalField(
        label='Saving Amount',
        max_digits=10, decimal_places=2,
        required=False, min_value=Decimal('0.00')
    )
    other_fee = forms.DecimalField(
        label='Other Fee',
        max_digits=10, decimal_places=2,
        required=False, min_value=Decimal('0.00')
    )
    payment_method = forms.ChoiceField(
        choices=[('cash', 'Cash'), ('bank', 'Bank Transfer')],
        required=True
    )
    remarks = forms.CharField(widget=forms.Textarea, required=False)
    
    # Loan repayment section
    loan_id = forms.ChoiceField(label='Loan', required=False)
    interest_paid = forms.DecimalField(
        label='Interest Paid',
        max_digits=10, decimal_places=2,
        required=False, min_value=Decimal('0.00')
    )
    principal_paid = forms.DecimalField(
        label='Principal Paid',
        max_digits=10, decimal_places=2,
        required=False, min_value=Decimal('0.00')
    )

    def __init__(self, *args, **kwargs):
        member = kwargs.pop('member', None)
        super().__init__(*args, **kwargs)

        if member:
            self.fields['member_id'].initial = member.member_id
            self.fields['member_name'].initial = f"{member.first_name} {member.last_name}"

            # Populate active loans only
            active_loans = Loan.objects.filter(customer=member, status='active')
            self.fields['loan_id'].choices = [('', '--- Select Loan ---')] + [
                (loan.id, f"Loan #{loan.id} | Remaining Principal: {loan.remaining_principal} | Interest Due: {loan.interest_to_pay}")
                for loan in active_loans
            ]
        else:
            self.fields['loan_id'].choices = [('', 'No active loans')]
