from django.contrib import admin
from expenses.models import Expense, TotalExpense
# Register your models here.
admin.site.register(Expense),
admin.site.register(TotalExpense)