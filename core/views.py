from django.shortcuts import render
from django.conf import settings

def home(request):
    return render(request, 'core/home.html', {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID
    })