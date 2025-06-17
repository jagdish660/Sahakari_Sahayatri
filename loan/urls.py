from django.urls import path
from loan import views as loan


urlpatterns = [
    path('', loan.loan_home, name='loan_home'),
    path('details/<int:id>', loan.loan_details, name='loan_details'),
    path('all/', loan.loan_all, name='loan_all'),
    path('update/<int:id>', loan.loan_update, name='loan_update'),
]