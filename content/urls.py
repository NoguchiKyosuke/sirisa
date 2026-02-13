"""
SIRISA コンテンツ配信URL設定
"""
from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    path('answer/<int:pk>/', views.SandboxedAnswerView.as_view(), name='sandboxed_answer'),
    path('cushion/', views.CushionPageView.as_view(), name='cushion'),
]
