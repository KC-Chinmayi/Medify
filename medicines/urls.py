from django.urls import path
from . import views

app_name = 'medicines'

urlpatterns = [
    path('search/', views.medicine_search, name='search'),
]
