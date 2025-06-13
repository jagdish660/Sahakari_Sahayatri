from django.shortcuts import render

# Create your views here.
def share_home(request):
    return render(request, 'share_home.html')