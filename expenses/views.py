from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from collections import defaultdict
from decimal import Decimal
from expenses.models import Expense, EXPENSE_CATEGORIES, TotalExpense
from saving.models import YearlyInterest
from django.contrib.auth.decorators import login_required

CATEGORY_LABELS = dict(EXPENSE_CATEGORIES)
# Crrate your views here.

# /expenses/
@login_required(login_url='loginpage')
def expenses_home(request):
    expenses = list(Expense.objects.all().order_by('-date'))
    total_expenses = sum(exp.amount for exp in Expense.objects.all())
    total_expenses += sum(exp.current_interest_amount for exp in YearlyInterest.objects.all())
    total_expenses += sum(exp.previous_interest_amount for exp in YearlyInterest.objects.all())
    for exp in expenses:
        exp.category_label = CATEGORY_LABELS.get(exp.category, exp.category)
    # Aggregate YearlyInterest entries by date
    interest_by_date = {}
    for interest in YearlyInterest.objects.all():
        if interest.date not in interest_by_date:
            interest_by_date[interest.date] = {
                'total_interest': Decimal('0.00'),
                'remarks': interest.remarks or 'Yearly Interest'
            }
        interest_by_date[interest.date]['total_interest'] += (
            interest.current_interest_amount + interest.previous_interest_amount
        )
    # Convert grouped interests to expense-like entries
    interest_expenses = []
    for date, data in interest_by_date.items():
        interest_expenses.append({
            'date': date,
            'category': 'Interest on Saving',
            'category_label': CATEGORY_LABELS.get('interest_saving', 'Interest'),
            'amount': data['total_interest'],
            'remarks': data['remarks']
        })
    # Combine and sort all expense-like objects
    combined_expenses = []
    for exp in expenses:
        combined_expenses.append({
            'date': exp.date,
            'category': exp.category,
            'category_label': exp.category_label, #Label for display
            'amount': exp.amount,
            'remarks': exp.remarks
        })
    combined_expenses += interest_expenses
    combined_expenses.sort(key=lambda x: x['date'], reverse=True)
    # Calculate totals per category
    totals = defaultdict(Decimal)
    for exp in combined_expenses:
        totals[exp['category']] += exp['amount']
    # Format totals with readable labels
    field_totals = [
        {'category': CATEGORY_LABELS.get(category, category), 'total': totals}
        for category, totals in totals.items()
    ]
    context = {
        'expenses': combined_expenses,
        'field_totals': field_totals,
        'total_yearly_interest': next(
            (item['total'] for item in field_totals if item['category'] == CATEGORY_LABELS.get('interest_saving', 'Interest')),
            Decimal('0.00')
        ),
        'total_expenses': total_expenses
    }
    return render(request, 'expenses_home.html', context)




CATEGORY_TOTAL_FIELD_MAP = {
    'stationary': 'total_stationary',
    'rent': 'total_rent',
    'freight': 'total_freight',
    'bonus': 'total_bonus',
    'interest_saving': 'total_interest_saving',
    'printing': 'total_printing',
    'photocopy': 'total_photocopy',
    'fuel': 'total_fuel',
    'miscellaneous': 'total_miscellaneous',
}


# /expenses/add/
@login_required(login_url='loginpage')
def expenses_add(request):
    if request.user.is_superuser or request.user.is_staff:
        if request.method == "POST":
            amount = request.POST.get('amount')
            category = request.POST.get('category')
            remarks = request.POST.get('remarks')
            payment_method = request.POST.get('payment_method', 'cash')

            if not amount:
                messages.error(request, "You must enter an amount.")
                return redirect('expenses_add')
            if not category:
                messages.error(request, "You must select a category.")
                return redirect('expenses_add')

            try:
                amount_decimal = Decimal(amount)
                today = timezone.now().date()

                # Save new Expense
                expense = Expense.objects.create(
                    amount=amount_decimal,
                    date=today,
                    category=category,
                    payment_method=payment_method,
                    remarks=remarks
                )
                messages.success(request, "Expense successfully added.")
                return redirect('expenses_home')
            except Exception as e:
                print(e)
                messages.error(request, f"Unexpected Error occurred: {str(e)}")
        return render(request, 'expenses_add.html')
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('home')
        
        
# /expenses/details/<str:category>/
@login_required(login_url='loginpage')
def expenses_details(request, category):
    if request.user.is_superuser or request.user.is_staff:
        if category == "interest on saving":
            expenses = YearlyInterest.objects.all().order_by('-date')
            for exp in expenses:
                prev = getattr(exp, 'previous_interest_amount', Decimal('0.00')) or Decimal('0.00')
                curr = getattr(exp, 'current_interest_amount', Decimal('0.00')) or Decimal('0.00')
                exp.total_interest = prev + curr
        else:
            category = category.lower()
            if category not in CATEGORY_TOTAL_FIELD_MAP:
                messages.error(request, "Invalid category specified.")
                return redirect('expenses_home')
            expenses = Expense.objects.filter(category=category).order_by('-date')
            if not expenses:
                messages.error(request, "No details found for this category.")
                return redirect('expenses_home')
        
            # total_amount = expenses.aggregate(Sum('amount'))['amount_sum'] or Decimal('0.00')
        context = {
                'expenses': expenses,
                
                'category': CATEGORY_LABELS.get(category, category),
                # 'total_amount': total_amount
            }
        return render(request, 'expenses_details.html', context)
    else:
        messages.error(request, "You're not allowed to perform this task.")
        return redirect('home')
    
    