from django.db import models
from django.utils import timezone
from customer.models import Member
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

class Loan(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Original loan principal")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4, help_text="Annual interest rate (e.g. 0.075 for 7.5%)")
    start_date = models.DateField(default=timezone.now)
    remaining_principal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_renewed = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_principal = self.amount
            self.last_renewed = self.start_date
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loan #{self.pk} for {self.customer} | Remaining Principal: {self.remaining_principal}"

    def monthly_interest(self):
        """Returns monthly interest based on current remaining principal"""
        return (self.remaining_principal * (self.interest_rate / Decimal('12'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

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


class Repayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    repayment_date = models.DateField(default=timezone.now)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total amount paid")
    principal_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        ordering = ['repayment_date']

    def save(self, *args, **kwargs):
        if self.principal_paid == 0 and self.interest_paid == 0:
            monthly_interest = self.loan.monthly_interest()

            if self.amount_paid >= monthly_interest:
                self.interest_paid = monthly_interest
                self.principal_paid = self.amount_paid - monthly_interest
            else:
                self.interest_paid = self.amount_paid
                self.principal_paid = Decimal('0.00')

            # Update remaining principal
            self.loan.remaining_principal = (
                Decimal(self.loan.remaining_principal) - Decimal(self.principal_paid)
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.loan.remaining_principal = max(self.loan.remaining_principal, Decimal('0.00'))
            self.loan.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return (f"Repayment on {self.repayment_date}: Total Paid={self.amount_paid}, "
                f"Principal={self.principal_paid}, Interest={self.interest_paid}")
