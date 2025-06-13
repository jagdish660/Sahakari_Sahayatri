from django.db import models
from datetime import date
from django.utils import timezone
from customer.models import Member
from decimal import Decimal
from django.db import transaction
from datetime import timedelta

# --- Utility: Map Gregorian date to Nepali fiscal year starting Shrawan 1 ---
def get_fiscal_year_starting_shrawan(dt: date) -> int:
    if dt.month > 7 or (dt.month == 7 and dt.day >= 16):
        return dt.year + 1
    return dt.year

def get_fiscal_year_start_end(year):
    start_date = date(year - 1, 7, 17)
    end_date = date(year, 7, 16)
    return start_date, end_date

# --- Models ---
class SavingBalance(models.Model):
    customer = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='saving_balance')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name} | Balance: Rs. {self.balance}"


class Deposit(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='deposits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ], default='cash')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer.name} | {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            balance_obj, _ = SavingBalance.objects.get_or_create(customer=self.customer)
            balance_obj.balance = Decimal(balance_obj.balance) + self.amount
            balance_obj.save()

    def get_fiscal_year(self):
        return get_fiscal_year_starting_shrawan(self.date)

    # Existing methods...
    # calculate_interest()
    # get_balance_until()

    class Meta:
        ordering = ['date']




class YearlyInterest(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='yearly_interests')
    year = models.IntegerField(help_text="Fiscal year starting in Shrawan")  # e.g., 2081
    previous_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    previous_interest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    current_interest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    date = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ('customer', 'year')
        ordering = ['date']

    def __str__(self):
        return f"{self.customer.name} | FY {self.year}"

    def get_shrawan_1_date(self):
        return date(self.year, 7, 17)

    def calculate_interest(self):
        from decimal import Decimal, ROUND_HALF_UP

        start_date, end_date = get_fiscal_year_start_end(self.year)
        shrawan_1 = self.get_shrawan_1_date()

        deposits = self.customer.deposits.filter(date__gte=start_date, date__lte=end_date)
        refunds = self.customer.saving_refunds.filter(refund_date__gte=start_date, refund_date__lte=end_date)

        transactions = []
        for d in deposits:
            transactions.append({'date': d.date, 'amount': d.amount})
        for r in refunds:
            transactions.append({'date': r.refund_date, 'amount': -r.amount_refunded})

        transactions.sort(key=lambda x: x['date'])

        pre_balance = Decimal('0.00')
        post_balance = Decimal('0.00')
        running_balance = Decimal('0.00')

        for tx in transactions:
            if tx['date'] < shrawan_1:
                running_balance += tx['amount']
                pre_balance = running_balance
            else:
                running_balance += tx['amount']
                post_balance = running_balance - pre_balance

        pre_rate = Decimal(self.previous_interest_rate) / Decimal('100')
        post_rate = Decimal(self.current_interest_rate) / Decimal('100')

        pre_interest = (pre_balance * pre_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        post_interest = (post_balance * post_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_interest = (pre_interest + post_interest).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            'pre_balance': pre_balance,
            'post_balance': post_balance,
            'pre_interest': pre_interest,
            'post_interest': post_interest,
            'total_interest': total_interest,
        }

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        interest_values = self.calculate_interest()
        self.previous_interest_amount = interest_values['pre_interest']
        self.current_interest_amount = interest_values['post_interest']
        super().save(*args, **kwargs)
        if is_new:
            total_interest = interest_values['pre_interest'] + interest_values['post_interest']
            balance_obj, _ = SavingBalance.objects.get_or_create(customer=self.customer)
            balance_obj.balance += total_interest
            balance_obj.save()



class SavingRefund(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='saving_refunds')
    amount_refunded = models.DecimalField(max_digits=12, decimal_places=2, help_text="Amount withdrawn/refunded from savings")
    refund_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ], default='cash')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer} | Refunded Rs. {self.amount_refunded} on {self.refund_date}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            balance_obj, _ = SavingBalance.objects.get_or_create(customer=self.customer)
            balance_obj.balance -= self.amount_refunded
            balance_obj.balance = max(balance_obj.balance, 0)
            balance_obj.save()

    class Meta:
        ordering = ['refund_date']


 