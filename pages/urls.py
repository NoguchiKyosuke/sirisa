"""
SIRISA 静的ページURL設定
"""
from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('how-to-use/', views.HowToUseView.as_view(), name='how_to_use'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
]
