from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('survey/<str:token>/',
         views.SatisfactionSurveyView.as_view(), name='survey_detail'),
]
