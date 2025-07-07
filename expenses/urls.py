from django.urls import path
from expenses import views as expenses


urlpatterns = [
    path('', expenses.expenses_home, name='expenses_home'),
    path('add/', expenses.expenses_add, name='expenses_add'),
    path('details/<str:category>/', expenses.expenses_details, name='expenses_details'),
    
]