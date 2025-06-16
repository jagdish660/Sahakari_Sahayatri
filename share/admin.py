from django.contrib import admin
from share.models import ShareCapital, ShareRefund, ShareBalance

# Register your models here.
admin.site.register(ShareCapital)
admin.site.register(ShareRefund)
admin.site.register(ShareBalance)