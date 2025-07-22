from django.urls import path
from share import views as share


urlpatterns = [
    
    path('', share.share_home, name='share_home'),
    path('add/', share.share_add_individual, name='share_add_individual'),
    path('add/<int:id>/', share.share_add, name='share_add'),
    path('refund/<int:id>/', share.share_refund, name='share_refund'),
    path('details/<int:id>/', share.share_details, name='share_details'),
]
