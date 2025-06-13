from django.shortcuts import render

# Create your views here.
def loan_home(request):
    return render(request, 'loan_home.html')