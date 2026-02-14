"""
SIRISA アカウントURL設定
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('firebase/callback/', views.FirebaseCallbackView.as_view(), name='firebase_callback'),
    path('firebase/email-link/', views.EmailLinkCallbackView.as_view(), name='email_link_callback'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/email/', views.EmailChangeView.as_view(), name='email_change'),
    path('profile/delete/', views.AccountDeleteView.as_view(), name='delete_account'),
    path('user/<str:username>/', views.UserProfileView.as_view(), name='user_profile'),
    path('user/<str:username>/report/', views.UserReportView.as_view(), name='user_report'),
]
