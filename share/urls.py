from django.urls import path
from share import views as share


urlpatterns = [
    
    path('', share.share_home, name='share_home'),
    
]