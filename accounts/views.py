"""
SIRISA アカウントビュー
ログイン、新規登録、メール認証、ログアウト
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.views import View

from .forms import LoginForm, RegisterForm, VerifyForm
from .models import EmailVerification
from .gmail_service import send_verification_email

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginView(View):
    """ログイン画面"""

    def get(self, request):
        # 認証済みユーザはホーム画面へリダイレクト（自動ログイン）
        if request.user.is_authenticated and request.user.is_verified:
            return redirect('home')
        form = LoginForm()
        return render(request, 'accounts/login.html', {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_deleted:
                    messages.error(request, 'このアカウントは無効です。')
                    return render(request, 'accounts/login.html', {'form': form})

                # 認証済みの場合はそのままログイン
                if user.is_verified:
                    login(request, user)
                    request.session.set_expiry(2592000)  # 30日間
                    return redirect('home')

                # 未認証の場合はメール認証画面へ
                request.session['pending_user_id'] = user.pk
                self._send_code(user)
                messages.info(request, '認証コードをメールに送信しました。')
                return redirect('accounts:verify')
            else:
                messages.error(request, 'メールアドレスまたはパスワードが正しくありません。')
        return render(request, 'accounts/login.html', {'form': form})

    def _send_code(self, user):
        """認証コードを生成して送信"""
        verification = EmailVerification(user=user)
        verification.save()
        send_verification_email(user, verification.code)


class RegisterView(View):
    """新規登録画面"""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 認証コード送信
            verification = EmailVerification(user=user)
            verification.save()
            send_verification_email(user, verification.code)

            request.session['pending_user_id'] = user.pk
            messages.success(request, '登録が完了しました。認証コードを入力してください。')
            return redirect('accounts:verify')
        return render(request, 'accounts/register.html', {'form': form})


class VerifyEmailView(View):
    """メール認証画面"""

    def get(self, request):
        user_id = request.session.get('pending_user_id')
        if not user_id:
            return redirect('accounts:login')
        form = VerifyForm()
        return render(request, 'accounts/verify.html', {'form': form})

    def post(self, request):
        user_id = request.session.get('pending_user_id')
        if not user_id:
            return redirect('accounts:login')

        form = VerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                user = User.objects.get(pk=user_id)
                verification = EmailVerification.objects.filter(
                    user=user,
                    code=code,
                    is_used=False,
                ).order_by('-created_at').first()

                if verification and verification.is_valid:
                    verification.is_used = True
                    verification.save(update_fields=['is_used'])
                    user.is_verified = True
                    user.save(update_fields=['is_verified'])

                    login(request, user)
                    request.session.set_expiry(2592000)  # 30日間
                    del request.session['pending_user_id']

                    messages.success(request, '認証が完了しました。ようこそ SIRISA へ！')
                    return redirect('home')
                else:
                    messages.error(request, '認証コードが無効または期限切れです。')
            except User.DoesNotExist:
                messages.error(request, 'ユーザが見つかりませんでした。')

        return render(request, 'accounts/verify.html', {'form': form})


class ResendCodeView(View):
    """認証コード再送信"""

    def post(self, request):
        user_id = request.session.get('pending_user_id')
        if not user_id:
            return redirect('accounts:login')

        try:
            user = User.objects.get(pk=user_id)
            # 60秒間隔制限
            recent = EmailVerification.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(seconds=60),
            ).exists()

            if recent:
                messages.warning(request, '再送信は60秒間隔でお願いします。')
            else:
                verification = EmailVerification(user=user)
                verification.save()
                send_verification_email(user, verification.code)
                messages.success(request, '認証コードを再送信しました。')
        except User.DoesNotExist:
            messages.error(request, 'ユーザが見つかりませんでした。')

        return redirect('accounts:verify')


class LogoutView(View):
    """ログアウト"""

    def get(self, request):
        logout(request)
        messages.info(request, 'ログアウトしました。')
        return redirect('accounts:login')
