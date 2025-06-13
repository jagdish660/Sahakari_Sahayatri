from django.urls import path
from saving import views as saving
from loan import views as loan
from share import views as share


urlpatterns = [
    
    path('', loan.loan_home, name='loan_home'),
    
]