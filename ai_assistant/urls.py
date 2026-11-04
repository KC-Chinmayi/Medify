from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('recommend/', views.get_ai_recommendation, name='recommend'),
]
