from django.urls import path
from . import views

app_name = 'blog'
urlpatterns = [
    path('', views.PostListView.as_view(), name='list'),
    path('<slug:slug>/', views.PostDetailView.as_view(), name='detail'),
    path('<slug:slug>/comment/', views.PostCommentCreateView.as_view(), name='comment_create'),
]