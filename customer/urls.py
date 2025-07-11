from django.urls import path
from django.shortcuts import redirect
from customer import views as customer


urlpatterns = [
    path('login/', customer.loginpage, name='loginpage'),
    path('logout/', customer.logout_user, name='logoutpage'),
    path('change_password/', customer.change_password, name='change_password'),
    path('reset_password_form/', customer.reset_password_form, name='reset_password_form'),
    path('reset_password/', customer.reset_password, name='reset_password'),
    path('verify_code/', customer.verify_code, name='verify_code'),
    
    path('', customer.home, name='home'),
    path('home/', customer.user_home, name='user_home'),
    path('about_me/', customer.about_me, name='about_me'),
    
    path('member/', customer.member_home, name='customer_home'),
    path('member/add/', customer.member_add, name='customer_add'),
    path('member/update/<int:id>/', customer.update_customer, name='customer_update'),
    path('member/delete/<int:id>/', customer.delete_customer, name='customer_delete'),
    path('member/details/update/<int:id>/', customer.user_update_customer, name='user_customer_update'),
    path('member/details/<int:member_id>/', customer.member_details, name='customer_details'),
]
