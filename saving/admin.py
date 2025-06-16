from django.contrib import admin
from saving.models import Deposit, YearlyInterest, SavingRefund, SavingBalance, OtherFee

# Register your models here.
admin.site.register(Deposit)
admin.site.register(YearlyInterest)
admin.site.register(SavingRefund)
admin.site.register(SavingBalance)
admin.site.register(OtherFee)
