"""
SIRISA ホームURL（ルートパス）
"""
from django.urls import path
from questions.views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
]
