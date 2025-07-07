# expenses/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Expense
from .utils import update_total_expense

@receiver(post_save, sender=Expense)
def update_total_expense_on_save(sender, instance, **kwargs):
    fiscal_year = instance.get_fiscal_year()
    update_total_expense(fiscal_year)

@receiver(post_delete, sender=Expense)
def update_total_expense_on_delete(sender, instance, **kwargs):
    fiscal_year = instance.get_fiscal_year()
    update_total_expense(fiscal_year)
