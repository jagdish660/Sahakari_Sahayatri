from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Loan

@login_required(login_url='loginpage')
def loan_home(request):
    # Only get loans with status "active"
    active_loans = Loan.objects.select_related('customer').filter(status='active').order_by('-id')
    # Calculate totals from active loans
    total_deployed = sum(loan.amount for loan in active_loans)
    current_year = timezone.now().year
    deployed_current_year = sum(
        loan.amount for loan in active_loans if loan.start_date.year == current_year
    )
    deployed_previous_year = total_deployed - deployed_current_year
    # Pagination
    paginator = Paginator(active_loans, 10)  # Show 10 loans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'loans': page_obj.object_list,  # Loans on current page
        'page_obj': page_obj,
        'total_deployed': total_deployed,
        'deployed_current_year': deployed_current_year,
        'deployed_previous_year': deployed_previous_year,
    }
    return render(request, 'loan_home.html', context)


def loan_all(request):
    loans = Loan.objects.select_related('customer').all().order_by('-id')
     # Pagination
    paginator = Paginator(loans,10)  # Show 10 loans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'loans': loans,
        'page_obj': page_obj,
    }
    return render(request, 'loan_all.html', context)


# /# loan/<int:id>/
@login_required(login_url='loginpage')
def loan_details(request, id):
    loan = Loan.objects.select_related('customer').get(id=id)
    context = {
        'loan': loan,
    }
    return render(request, 'loan_details.html', context)
