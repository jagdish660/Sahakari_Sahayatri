from django.urls import path
from saving import views as saving


urlpatterns = [
    path('', saving.home, name='home'),
    path('saving/', saving.saving_home, name='saving_home'),
    path('saving/<int:member_id>/', saving.saving_details, name='saving_details'),
    path('transaction/', saving.transactions, name='transactions'),
    path('saving/add/<int:member_id>/', saving.saving_add, name='saving_add'),
    path('saving/interest/<int:member_id>/', saving.saving_yearly_interest, name='saving_interest_yearly'),
    path('saving/interest/', saving.saving_interest, name='saving_interest'),
]
