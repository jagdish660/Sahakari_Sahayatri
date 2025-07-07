from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

# Utility function to get Nepali fiscal year starting Shrawan 1 (July 17)
def get_fiscal_year_starting_shrawan(dt: date) -> int:
    if dt.month > 7 or (dt.month == 7 and dt.day >= 16):
        return dt.year + 1
    return dt.year

def get_fiscal_year_start_end(year):
    start_date = date(year - 1, 7, 17)
    end_date = date(year, 7, 16)
    return start_date, end_date

# Expense Categories
EXPENSE_CATEGORIES = [
    ('stationary', 'Stationary'),
    ('rent', 'Rent'),
    ('freight', 'Freight'),
    ('bonus', 'Bonus'),
    ('interest_saving', 'Interest on Saving'),
    ('printing', 'Printing'),
    ('photocopy', 'Photocopy'),
    ('fuel', 'Fuel'),
    ('miscellaneous', 'Miscellaneous'),
]

PAYMENT_METHODS = [
    ('cash', 'Cash'),
    ('cheque', 'Cheque'),
    ('bank_transfer', 'Bank Transfer'),
]

class Expense(models.Model):
    date = models.DateField(default=timezone.now)
    category = models.CharField(max_length=30, choices=EXPENSE_CATEGORIES)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='cash')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)

    def get_fiscal_year(self):
        return get_fiscal_year_starting_shrawan(self.date)

    def __str__(self):
        return f"{self.get_category_display()} - Rs. {self.amount} on {self.date}"

    class Meta:
        ordering = ['-date']


class TotalExpense(models.Model):
    fiscal_year = models.IntegerField(unique=True)
    total_stationary = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_rent = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_freight = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_bonus = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_interest_saving = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_printing = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_photocopy = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_fuel = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_miscellaneous = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_overall = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Total Expense for FY {self.fiscal_year} | Rs. {self.total_overall}"

    class Meta:
        ordering = ['-fiscal_year']
