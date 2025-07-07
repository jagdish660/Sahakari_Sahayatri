from django.db.models import Sum
from .models import Expense, TotalExpense, get_fiscal_year_start_end, EXPENSE_CATEGORIES
from decimal import Decimal

def update_total_expense(fiscal_year):
    start_date, end_date = get_fiscal_year_start_end(fiscal_year)
    expenses = Expense.objects.filter(date__range=(start_date, end_date))

    # Initialize all categories to 0
    totals = {f"total_{cat[0]}": Decimal('0.00') for cat in EXPENSE_CATEGORIES}

    # Aggregate sums per category
    grouped = expenses.values('category').annotate(total=Sum('amount'))
    for entry in grouped:
        field = f"total_{entry['category']}"
        totals[field] = entry['total'] or Decimal('0.00')

    # Compute total overall
    total_overall = sum(totals.values())

    # Create or update the TotalExpense record
    TotalExpense.objects.update_or_create(
        fiscal_year=fiscal_year,
        defaults={**totals, 'total_overall': total_overall}
    )
