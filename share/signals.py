from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from share.models import ShareCapital, ShareRefund, ShareBalance
from customer.models import Transaction, Member  # Adjust if your app is named differently


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
        # Update Share Balance
        update_share_balance(instance.customer)

        # Create Transaction for purchase
        Transaction.objects.create(
            member=instance.customer,
            date=instance.purchase_date,
            amount=Decimal(instance.share_amount),
            share=Decimal(instance.share_amount),
            remarks=f"Share purchased on {instance.purchase_date}",
            payment_method='cash'
        )


@receiver(post_save, sender=ShareRefund)
def update_balance_on_refund(sender, instance, created, **kwargs):
    if created:
        # Update Share Balance
        update_share_balance(instance.customer)

        # Create Transaction for refund (negative values)
        Transaction.objects.create(
            member=instance.customer,
            date=instance.refund_date,
            amount=Decimal(-instance.refund_amount),
            share=Decimal(-instance.refund_amount),
            remarks=f"Share refunded on {instance.refund_date}",
            payment_method='cash'
        )
