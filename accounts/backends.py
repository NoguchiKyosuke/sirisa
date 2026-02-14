"""
SIRISA カスタム認証バックエンド
Firebase ID トークンでユーザを認証する
"""
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

from .firebase_auth import verify_id_token

logger = logging.getLogger(__name__)
User = get_user_model()


class FirebaseAuthBackend(BaseBackend):
    """
    Firebase ID トークンを検証して Django ユーザを返す認証バックエンド。

    usage:
        user = authenticate(request, firebase_id_token=token)
    """

    def authenticate(self, request, firebase_id_token=None, **kwargs):
        if firebase_id_token is None:
            return None

        decoded = verify_id_token(firebase_id_token)
        if decoded is None:
            return None

        uid = decoded.get('uid')
        email = decoded.get('email')
        if not uid or not email:
            logger.warning('Firebase token missing uid or email')
            return None

        # firebase_uid で既存ユーザを検索
        try:
            user = User.objects.get(firebase_uid=uid, is_deleted=False)
            # メールが変わっていたら同期
            if user.email != email:
                user.email = email
                user.save(update_fields=['email'])
            return user
        except User.DoesNotExist:
            pass

        # email で既存ユーザを検索（既存アカウントの Firebase 移行）
        try:
            user = User.objects.get(email=email, is_deleted=False)
            user.firebase_uid = uid
            user.is_verified = True
            user.save(update_fields=['firebase_uid', 'is_verified'])
            logger.info('Linked existing user %s to Firebase uid %s', email, uid)
            return user
        except User.DoesNotExist:
            pass

        # 新規ユーザ — LoginView/RegisterView 側で作成するので
        # ここでは None を返す（callback view で処理）
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id, is_deleted=False)
        except User.DoesNotExist:
            return None
