from django.urls import path
from customer import views as customer


urlpatterns = [
    path('login/', customer.loginpage, name='loginpage'),
    path('logout/', customer.logout_user, name='logoutpage'),
    path('', customer.member_home, name='customer_home'),
    path('add/', customer.member_add, name='customer_add'),
    path('update/<int:id>/', customer.update_customer, name='customer_update'),
    path('delete/<int:id>/', customer.delete_customer, name='customer_delete'),
    path('details/update/<int:id>/', customer.user_update_customer, name='user_customer_update'),
    path('details/<int:member_id>/', customer.member_details, name='customer_details'),
    path('change_password/', customer.change_password, name='change_password'),
]
