from django.urls import path
from customer import views as customer


urlpatterns = [
    
    path('', customer.member_home, name='customer_home'),
    path('add/', customer.member_add, name='customer_add'),
    path('update/<int:id>/', customer.update_member, name='customer_update'),
    path('members/<int:member_id>/', customer.member_details, name='customer_details'),
]