from django.db import models
from datetime import date
from django.contrib.auth.models import User
from decimal import Decimal

class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member_profile')
    member_id = models.IntegerField(unique=True, primary_key=True)
    first_name = models.CharField(max_length=30, blank=False)
    middle_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=False)
    email = models.EmailField(unique=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True)
    address = models.TextField(blank=False)
    date_of_birth = models.DateField(blank=True, null=True)
    citizenship_number = models.CharField(max_length=20, unique=True, blank=False)
    occupation = models.CharField(max_length=100, blank=True)
    date_joined = models.DateField(null=True, blank=True)
    # This stores the full name
    name = models.CharField(max_length=100, blank=False, editable=False)

    def save(self, *args, **kwargs):
        parts = [self.first_name.strip()]
        if self.middle_name:
            parts.append(self.middle_name.strip())
        parts.append(self.last_name.strip())
        self.name = " ".join(parts)

        if not self.date_joined:
            self.date_joined = date.today()
        super().save(*args, **kwargs)
    def __str__(self):
        return f"({self.member_id}) - {self.name}"
    class Meta:
        ordering = ['member_id']  # Ascending order
        # ordering = ['-member_id']  # For descending order



class Transaction(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    saving_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    loan_repayment = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    share = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    other_fee = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('interest', 'Interest'),
        ('cheque', 'Cheque'),
    ], default='cash')
    remarks = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        latest = Transaction.objects.filter(member=self.member).order_by('-date').first()

        amount = Decimal(self.amount)
        loan_repayment = Decimal(self.loan_repayment)
        interest_paid = Decimal(self.interest_paid)
        latest_saving_balance = Decimal(latest.saving_balance) if latest else Decimal('0.00')

        if latest and latest.pk != self.pk:
            self.saving_balance = latest_saving_balance + amount - loan_repayment - interest_paid
        else:
            self.saving_balance = amount - loan_repayment - interest_paid

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.name} | Rs. {self.amount} on {self.date}"

    class Meta:
        ordering = ['-date']
