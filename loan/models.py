from django.db import models
from django.utils import timezone
from customer.models import Member
from core.utils import gregorian_to_nepali_approx
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

class Loan(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Original loan principal")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual interest rate (e.g. 0.075 for 7.5%)")
    start_date = models.DateField(default=timezone.now)
    remaining_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], default='active', help_text="Current status of the loan")
    remarks = models.TextField(blank=True, null=True)
    
    last_renewed = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_principal = self.amount
            self.last_renewed = self.start_date
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loan #{self.pk} for {self.customer} | Remaining Principal: {self.remaining_principal}"

    def monthly_interest(self):
        """Returns monthly interest based on current remaining principal."""
        # Convert percentage (e.g., 10) to decimal (e.g., 0.10)
        monthly_rate = (self.interest_rate / Decimal('100.0')) / Decimal('12.0')
        return (self.remaining_principal * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def update_status_based_on_principal(self):
        self.status = 'closed' if self.remaining_principal == Decimal('0.00') else 'active'
        self.save()

    def is_shrawan_renewal_due(self):
        today = date.today()
        if date(today.year, 7, 16) <= today <= date(today.year, 8, 15):
            if not self.last_renewed or self.last_renewed.year < today.year:
                return True
        return False

    def apply_renewal_charge(self):
        if self.is_shrawan_renewal_due():
            renewal_fee = (self.amount * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.remaining_principal += renewal_fee
            self.last_renewed = date.today()
            self.save()
            return renewal_fee
        return Decimal('0.00')

    def interest_to_pay(self):
        """
        Calculate interest based on full Nepali months between last payment/renewal and today.
        """
        last_payment_date = self.repayments.last().repayment_date if self.repayments.exists() else self.last_renewed or self.start_date
        today = date.today()

        last_np_year, last_np_month = gregorian_to_nepali_approx(last_payment_date)
        today_np_year, today_np_month = gregorian_to_nepali_approx(today)

        # Calculate Nepali month difference
        months_passed = (today_np_year - last_np_year) * 12 + (today_np_month - last_np_month)

        if months_passed <= 0:
            return Decimal('0.00')

        monthly_interest = self.monthly_interest()
        total_interest = (monthly_interest * months_passed).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return total_interest


class Repayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    previous_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    repayment_date = models.DateField(default=timezone.now)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total amount paid")
    principal_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remaining_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-repayment_date']

    def save(self, *args, **kwargs):
        if self.principal_paid == 0 and self.interest_paid == 0:
            monthly_interest = self.loan.monthly_interest()

            if self.amount_paid >= monthly_interest:
                self.interest_paid = monthly_interest
                self.principal_paid = self.amount_paid - monthly_interest
            else:
                self.interest_paid = self.amount_paid
                self.principal_paid = Decimal('0.00')

        self.previous_principal = self.loan.remaining_principal

        # Update loan's remaining principal
        new_remaining = (
            Decimal(self.loan.remaining_principal) - Decimal(self.principal_paid)
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        new_remaining = max(new_remaining, Decimal('0.00'))

        self.loan.remaining_principal = new_remaining
        self.loan.status = 'closed' if new_remaining == Decimal('0.00') else 'active'
        self.loan.save()

        # Store updated remaining principal in this repayment record
        self.remaining_principal = new_remaining

        super().save(*args, **kwargs)

    def __str__(self):
        return (f"Repayment on {self.repayment_date}: Total Paid={self.amount_paid}, "
                f"Principal={self.principal_paid}, Interest={self.interest_paid}")

