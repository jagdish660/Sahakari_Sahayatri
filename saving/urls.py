from django.urls import path
from saving import views as saving


urlpatterns = [
    
    path('saving/', saving.saving_home, name='saving_home'),
    path('saving/<int:member_id>/', saving.saving_details, name='saving_details'),
    path('', saving.transactions, name='transactions'),
]