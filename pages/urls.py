from django.urls import path

from . import views

app_name = 'pages'

urlpatterns = [
    path('<slug:slug>/', views.StaticPageDetailView.as_view(), name='detail'),
]