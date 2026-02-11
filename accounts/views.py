"""
SIRISA アカウントビュー
パスワードレス認証（メール認証コードでログイン・登録）
プロフィール管理
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.views import View

from .forms import LoginForm, RegisterForm, VerifyForm, ProfileForm, EmailChangeForm
from .models import EmailVerification
from .gmail_service import send_verification_email

logger = logging.getLogger(__name__)
User = get_user_model()


class LoginView(View):
    """ログイン画面（パスワードレス：メールに認証コード送信）"""

    def get(self, request):
        if request.user.is_authenticated and request.user.is_verified:
            return redirect('home')
        form = LoginForm()
        return render(request, 'accounts/login.html', {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email, is_deleted=False, is_verified=True)
            except User.DoesNotExist:
                messages.error(request, 'このメールアドレスは登録されていません。')
                return render(request, 'accounts/login.html', {'form': form})

            # 認証コード送信してverify画面へ
            request.session['pending_user_id'] = user.pk
            request.session['auth_flow'] = 'login'
            self._send_code(user)
            messages.info(request, '認証コードをメールに送信しました。')
            return redirect('accounts:verify')
        return render(request, 'accounts/login.html', {'form': form})

    def _send_code(self, user):
        verification = EmailVerification(user=user)
        verification.save()
        send_verification_email(user, verification.code)


class RegisterView(View):
    """新規登録画面（パスワードなし）"""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = RegisterForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            verification = EmailVerification(user=user)
            verification.save()
            send_verification_email(user, verification.code)

            request.session['pending_user_id'] = user.pk
            request.session['auth_flow'] = 'register'
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
                    self._cleanup_session(request)

                    messages.success(request, '認証が完了しました。ようこそ SIRISA へ！')
                    return redirect('home')
                else:
                    messages.error(request, '認証コードが無効または期限切れです。')
            except User.DoesNotExist:
                messages.error(request, 'ユーザが見つかりませんでした。')

        return render(request, 'accounts/verify.html', {'form': form})

    def _cleanup_session(self, request):
        for key in ('pending_user_id', 'auth_flow', 'email_change_to'):
            request.session.pop(key, None)


class ResendCodeView(View):
    """認証コード再送信"""

    def post(self, request):
        user_id = request.session.get('pending_user_id')
        if not user_id:
            return redirect('accounts:login')

        try:
            user = User.objects.get(pk=user_id)
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


class ProfileView(LoginRequiredMixin, View):
    """プロフィール設定画面"""
    login_url = '/accounts/login/'

    def get(self, request):
        form = ProfileForm(instance=request.user)
        email_form = EmailChangeForm(user=request.user)
        return render(request, 'accounts/profile.html', {
            'form': form,
            'email_form': email_form,
        })

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        email_form = EmailChangeForm(user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'ユーザ名を更新しました。')
            return redirect('accounts:profile')
        return render(request, 'accounts/profile.html', {
            'form': form,
            'email_form': email_form,
        })


class EmailChangeView(LoginRequiredMixin, View):
    """メールアドレス変更（認証コード送信後に変更）"""
    login_url = '/accounts/login/'

    def post(self, request):
        form = EmailChangeForm(request.POST, user=request.user)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']
            # セッションに保存して認証コードを送信
            request.session['email_change_to'] = new_email
            request.session['pending_user_id'] = request.user.pk
            request.session['auth_flow'] = 'email_change'
            verification = EmailVerification(user=request.user)
            verification.save()
            # 現在のメールに認証コード送信
            send_verification_email(request.user, verification.code)
            messages.info(request, '現在のメールアドレスに認証コードを送信しました。')
            return redirect('accounts:verify_email_change')
        profile_form = ProfileForm(instance=request.user)
        return render(request, 'accounts/profile.html', {
            'form': profile_form,
            'email_form': form,
        })


class VerifyEmailChangeView(LoginRequiredMixin, View):
    """メールアドレス変更の認証"""
    login_url = '/accounts/login/'

    def get(self, request):
        if 'email_change_to' not in request.session:
            return redirect('accounts:profile')
        form = VerifyForm()
        return render(request, 'accounts/verify.html', {
            'form': form,
            'is_email_change': True,
        })

    def post(self, request):
        if 'email_change_to' not in request.session:
            return redirect('accounts:profile')

        form = VerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            verification = EmailVerification.objects.filter(
                user=request.user,
                code=code,
                is_used=False,
            ).order_by('-created_at').first()

            if verification and verification.is_valid:
                verification.is_used = True
                verification.save(update_fields=['is_used'])
                new_email = request.session.pop('email_change_to')
                request.session.pop('pending_user_id', None)
                request.session.pop('auth_flow', None)
                request.user.email = new_email
                request.user.save(update_fields=['email'])
                messages.success(request, 'メールアドレスを変更しました。')
                return redirect('accounts:profile')
            else:
                messages.error(request, '認証コードが無効または期限切れです。')

        return render(request, 'accounts/verify.html', {
            'form': form,
            'is_email_change': True,
        })


class AccountDeleteView(LoginRequiredMixin, View):
    """アカウント削除（論理削除）"""
    login_url = '/accounts/login/'

    def post(self, request):
        user = request.user
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.save(update_fields=['is_deleted', 'deleted_at'])
        logout(request)
        messages.info(request, 'アカウントを削除しました。')
        return redirect('accounts:login')
