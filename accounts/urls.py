"""
SIRISA アカウントURL設定
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify/', views.VerifyEmailView.as_view(), name='verify'),
    path('verify/resend/', views.ResendCodeView.as_view(), name='resend_code'),
    path('verify/email-change/', views.VerifyEmailChangeView.as_view(), name='verify_email_change'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/email/', views.EmailChangeView.as_view(), name='email_change'),
    path('profile/delete/', views.AccountDeleteView.as_view(), name='delete_account'),
]
