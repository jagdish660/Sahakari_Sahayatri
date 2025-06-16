from django.db.models.signals import post_save
from django.dispatch import receiver
from share.models import ShareCapital, ShareRefund, ShareBalance
from django.utils import timezone
from django.db.models import Sum

def update_share_balance(customer):
    total_purchased = customer.share_purchases.aggregate(Sum('share_amount'))['share_amount__sum'] or 0
    total_refunded = customer.share_refunds.aggregate(Sum('refund_amount'))['refund_amount__sum'] or 0
    balance = total_purchased - total_refunded

    ShareBalance.objects.update_or_create(
        customer=customer,
        defaults={
            'balance': balance,
            'last_updated': timezone.now()
        }
    )

@receiver(post_save, sender=ShareCapital)
def update_balance_on_purchase(sender, instance, created, **kwargs):
    if created:
        update_share_balance(instance.customer)

@receiver(post_save, sender=ShareRefund)
def update_balance_on_refund(sender, instance, created, **kwargs):
    if created:
        update_share_balance(instance.customer)
