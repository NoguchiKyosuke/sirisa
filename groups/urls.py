"""
SIRISA グループURL設定
"""
from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.GroupListView.as_view(), name='list'),
    path('new/', views.GroupCreateView.as_view(), name='create'),
    path('<int:pk>/', views.GroupDetailView.as_view(), name='detail'),
    path('<int:pk>/leave/', views.GroupLeaveView.as_view(), name='leave'),
    path('<int:pk>/delete/', views.GroupDeleteView.as_view(), name='delete'),
    path('<int:pk>/regenerate-code/', views.GroupRegenerateCodeView.as_view(), name='regenerate_code'),
    path('<int:pk>/remove/<int:user_id>/', views.GroupRemoveMemberView.as_view(), name='remove_member'),
    path('join/', views.GroupJoinView.as_view(), name='join'),
]
