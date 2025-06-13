from django.db import models
from django.utils import timezone
from customer.models import Member

# Create your models here.

class ShareCapital(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='share_purchases')
    share_amount = models.IntegerField(help_text="Share Amount at purchase time")
    purchase_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.customer} | {self.share_amount} shares on {self.purchase_date}"

class ShareRefund(models.Model):
    customer = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='share_refunds')
    refund_amount = models.IntegerField(help_text="Amount refunded for shares")
    refund_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.customer} | Refunded {self.refund_amount} shares on {self.refund_date}"


