from django.urls import path
from saving import views as saving


urlpatterns = [
        
    path('', saving.saving_home, name='saving_home'),
    path('<int:member_id>/', saving.saving_details, name='saving_details'),
    path('add/<int:member_id>/', saving.saving_add, name='saving_add'),
    # path('saving/interest/summary', saving.saving_yearly_interest, name='saving_interest_yearly'),
    path('interest/', saving.saving_interest, name='saving_interest'),
]
