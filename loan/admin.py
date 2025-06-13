from django.contrib import admin
from loan.models import Loan, Repayment

# Register your models here.
admin.site.register(Loan)
admin.site.register(Repayment)