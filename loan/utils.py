from decimal import Decimal
from django.db.models import Sum
from datetime import date
from loan.models import Repayment, Loan
 # Import your own helper

def interest_to_pay(loan: Loan) -> Decimal:
    """
    Calculates the total interest accrued since the last interest payment,
    minus the total interest paid in that period.
    """
    today = date.today()
    last_date = loan.repayments.last().repayment_date if loan.repayments.exists() else loan.last_renewed or loan.start_date
    days_elapsed = (today - last_date).days

    # Simple daily interest formula: (P * R * T) / 36500
    principal = loan.remaining_principal
    rate = loan.interest_rate
    accrued_interest = (principal * rate * Decimal(days_elapsed)) / Decimal('36500')

    # Total interest already paid through repayments
    paid_interest = Repayment.objects.filter(loan=loan).aggregate(
        total=Sum('interest_paid')
    )['total'] or Decimal('0.00')

    # Net interest remaining to pay
    remaining_interest = accrued_interest - paid_interest
    return max(remaining_interest.quantize(Decimal('0.01')), Decimal('0.00'))



def latest_interest_paid_date(loan: Loan) -> date:
    """
    Returns the most recent repayment date where interest > 0.
    Falls back to last_renewed or start_date if no interest has ever been paid.
    """
    latest_repayment_with_interest = loan.repayments.filter(
        interest_paid__gt=0
    ).order_by('-repayment_date').first()

    if latest_repayment_with_interest:
        return latest_repayment_with_interest.repayment_date

    # Fallbacks if no interest was paid yet
    if loan.last_renewed:
        return loan.last_renewed

    return loan.start_date

