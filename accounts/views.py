"""
SIRISA アカウントビュー
Firebase 認証（メールリンク + Google サインイン）
プロフィール管理
"""
import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .forms import RegisterForm, ProfileForm, EmailChangeForm, UserReportForm
from .models import UserReport
from .firebase_auth import verify_id_token

logger = logging.getLogger(__name__)
User = get_user_model()


# ── Firebase 認証ビュー ──────────────────────────────────────


class LoginView(View):
    """ログイン画面（Firebase 認証: メール/パスワード / Google）"""

    def get(self, request):
        if request.user.is_authenticated and request.user.is_verified:
            return redirect('home')
        return render(request, 'accounts/login.html', {
            'firebase_api_key': settings.FIREBASE_API_KEY,
            'firebase_auth_domain': settings.FIREBASE_AUTH_DOMAIN,
            'firebase_project_id': settings.FIREBASE_PROJECT_ID,
        })


class RegisterView(View):
    """
    新規登録画面 — Firebase 認証後、ユーザ名を設定する。
    Firebase 認証 → callback でセッションに仮情報保存 → ここでユーザ名入力。
    """

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')

        # Firebase 認証済みか確認
        firebase_email = request.session.get('firebase_email')
        if not firebase_email:
            # 未認証 → ログインページへ
            return redirect('accounts:login')

        form = RegisterForm(initial={'email': firebase_email})
        return render(request, 'accounts/register.html', {
            'form': form,
            'firebase_email': firebase_email,
        })

    def post(self, request):
        firebase_uid = request.session.get('firebase_uid')
        firebase_email = request.session.get('firebase_email')
        if not firebase_uid or not firebase_email:
            messages.error(request, 'Firebase認証が必要です。')
            return redirect('accounts:login')

        form = RegisterForm(request.POST)
        # email を Firebase から取得した値に固定
        form.data = form.data.copy()
        form.data['email'] = firebase_email

        if form.is_valid():
            # 削除済みユーザの firebase_uid をクリア（unique 制約対策）
            User.objects.filter(firebase_uid=firebase_uid, is_deleted=True).update(firebase_uid=None)
            user = form.save(commit=False)
            user.firebase_uid = firebase_uid
            user.is_verified = True
            user.set_unusable_password()
            user.save()

            # セッションクリア
            request.session.pop('firebase_uid', None)
            request.session.pop('firebase_email', None)
            request.session.pop('firebase_name', None)

            login(request, user, backend='accounts.backends.FirebaseAuthBackend')
            request.session.set_expiry(2592000)  # 30日間
            messages.success(request, '登録が完了しました。ようこそ SIRISA へ！')
            return redirect('home')

        return render(request, 'accounts/register.html', {
            'form': form,
            'firebase_email': firebase_email,
        })


@method_decorator(csrf_exempt, name='dispatch')
class FirebaseCallbackView(View):
    """
    Firebase ID トークンを受け取り Django セッションにログインする。

    POST /accounts/firebase/callback/
    Body: { "idToken": "..." }
    Response: { "status": "ok", "redirect": "/", "action": "login" }
              { "status": "ok", "redirect": "/accounts/register/", "action": "register" }
              { "status": "error", "message": "..." }
    """

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logger.warning('FirebaseCallback: invalid JSON body')
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

        id_token = body.get('idToken')
        if not id_token:
            logger.warning('FirebaseCallback: missing idToken')
            return JsonResponse({'status': 'error', 'message': 'idToken is required'}, status=400)

        # Firebase ID トークン検証
        decoded = verify_id_token(id_token)
        if decoded is None:
            logger.warning('FirebaseCallback: token verification failed')
            return JsonResponse({'status': 'error', 'message': '認証に失敗しました。'}, status=401)

        uid = decoded.get('uid')
        email = decoded.get('email')
        name = decoded.get('name', '')
        logger.info('FirebaseCallback: token verified uid=%s email=%s', uid, email)

        if not email:
            return JsonResponse({'status': 'error', 'message': 'メールアドレスが取得できませんでした。'}, status=400)

        # 削除済みユーザの firebase_uid をクリア（再登録を許可）
        User.objects.filter(firebase_uid=uid, is_deleted=True).update(firebase_uid=None)

        # Firebase UID で既存ユーザを検索
        user = None
        try:
            user = User.objects.get(firebase_uid=uid, is_deleted=False)
            # メールが変わっていたら同期
            if user.email != email:
                user.email = email
                user.save(update_fields=['email'])
            logger.info('FirebaseCallback: found user by firebase_uid=%s', uid)
        except User.DoesNotExist:
            pass

        # email で既存ユーザを検索（Firebase 移行中の既存アカウント）
        if user is None:
            try:
                user = User.objects.get(email=email, is_deleted=False)
                user.firebase_uid = uid
                user.is_verified = True
                user.save(update_fields=['firebase_uid', 'is_verified'])
                logger.info('FirebaseCallback: linked existing user %s to firebase_uid=%s', email, uid)
            except User.DoesNotExist:
                pass

        if user is not None:
            # 既存ユーザ → ログイン
            login(request, user, backend='accounts.backends.FirebaseAuthBackend')
            request.session.set_expiry(2592000)  # 30日間
            logger.info('FirebaseCallback: login success for %s', email)
            return JsonResponse({
                'status': 'ok',
                'redirect': '/',
                'action': 'login',
            })
        else:
            # 新規ユーザ → セッションに Firebase 情報を保存し登録画面へ
            request.session['firebase_uid'] = uid
            request.session['firebase_email'] = email
            request.session['firebase_name'] = name
            logger.info('FirebaseCallback: new user %s → register', email)
            return JsonResponse({
                'status': 'ok',
                'redirect': '/accounts/register/',
                'action': 'register',
            })


# ── 既存ビュー ──────────────────────────────────


class LogoutView(View):
    """ログアウト"""

    def get(self, request):
        logout(request)
        messages.info(request, 'ログアウトしました。')
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, View):
    """プロフィール設定画面"""
    login_url = '/accounts/login/'

    @staticmethod
    def _mask_email(email):
        """メールアドレスをマスクする（先頭1文字以外を*に）"""
        local, domain = email.split('@')
        masked_local = local[0] + '*' * (len(local) - 1) if len(local) > 1 else local
        return f'{masked_local}@{domain}'

    def get(self, request):
        form = ProfileForm(instance=request.user)
        email_form = EmailChangeForm(user=request.user)
        return render(request, 'accounts/profile.html', {
            'form': form,
            'email_form': email_form,
            'masked_email': self._mask_email(request.user.email),
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
            'masked_email': self._mask_email(request.user.email),
        })


class EmailChangeView(LoginRequiredMixin, View):
    """
    メールアドレス変更。
    Firebase 側のメールも変更が必要なため、
    利用者には Firebase の再認証を案内する。
    """
    login_url = '/accounts/login/'

    def post(self, request):
        form = EmailChangeForm(request.POST, user=request.user)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']
            request.user.email = new_email
            request.user.save(update_fields=['email'])
            messages.success(request, 'メールアドレスを変更しました。Firebase 側のメールアドレスも更新してください。')
            return redirect('accounts:profile')
        profile_form = ProfileForm(instance=request.user)
        return render(request, 'accounts/profile.html', {
            'form': profile_form,
            'email_form': form,
        })


class AccountDeleteView(LoginRequiredMixin, View):
    """アカウント削除（論理削除）"""
    login_url = '/accounts/login/'

    def post(self, request):
        user = request.user
        user.anonymize_for_deletion()
        logout(request)
        messages.info(request, 'アカウントを削除しました。')
        return redirect('accounts:login')


class UserProfileView(LoginRequiredMixin, View):
    """他ユーザのプロフィール閲覧"""
    login_url = '/accounts/login/'

    def get(self, request, username):
        target_user = User.objects.filter(username=username, is_deleted=False).first()
        if not target_user:
            messages.error(request, 'ユーザが見つかりませんでした。')
            return redirect('home')

        # 自分自身のプロフィールなら設定画面にリダイレクト
        if target_user == request.user:
            return redirect('accounts:profile')

        from questions.models import Question, Answer
        question_count = Question.objects.filter(user=target_user, is_deleted=False).count()
        answer_count = Answer.objects.filter(user=target_user, is_deleted=False).count()

        report_form = UserReportForm()

        return render(request, 'accounts/user_profile.html', {
            'target_user': target_user,
            'question_count': question_count,
            'answer_count': answer_count,
            'report_form': report_form,
        })


class UserReportView(LoginRequiredMixin, View):
    """ユーザ通報"""
    login_url = '/accounts/login/'

    def post(self, request, username):
        target_user = User.objects.filter(username=username, is_deleted=False).first()
        if not target_user:
            messages.error(request, 'ユーザが見つかりませんでした。')
            return redirect('home')

        if target_user == request.user:
            messages.error(request, '自分自身を通報することはできません。')
            return redirect('accounts:user_profile', username=username)

        # 重複通報チェック（同じユーザへの通報は1日1回まで）
        from datetime import timedelta
        recent_report = UserReport.objects.filter(
            reporter=request.user,
            reported_user=target_user,
            created_at__gte=timezone.now() - timedelta(hours=24),
        ).exists()
        if recent_report:
            messages.warning(request, '同じユーザへの通報は24時間に1回までです。')
            return redirect('accounts:user_profile', username=username)

        form = UserReportForm(request.POST)
        if form.is_valid():
            UserReport.objects.create(
                reporter=request.user,
                reported_user=target_user,
                reason=form.cleaned_data['reason'],
                detail=form.cleaned_data.get('detail', ''),
            )
            messages.success(request, 'ユーザを通報しました。ご報告ありがとうございます。')
        else:
            messages.error(request, '通報内容に不備があります。')

        return redirect('accounts:user_profile', username=username)
