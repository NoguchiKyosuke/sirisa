"""
SIRISA Firebase 認証サービス
Firebase Admin SDK による ID トークン検証
"""
import logging
import firebase_admin
from firebase_admin import auth, credentials
from django.conf import settings

logger = logging.getLogger(__name__)

# Firebase Admin SDK 初期化（GCE 上ではデフォルト認証情報を使用）
_app = None


def _get_app():
    """Firebase Admin App をシングルトンで取得する"""
    global _app
    if _app is None:
        try:
            _app = firebase_admin.get_app()
        except ValueError:
            # まだ初期化されていない場合
            _app = firebase_admin.initialize_app(options={
                'projectId': getattr(settings, 'FIREBASE_PROJECT_ID', 'sirisa'),
            })
            logger.info('Firebase Admin SDK を初期化しました (project=%s)',
                        _app.project_id)
    return _app


def verify_id_token(id_token: str) -> dict | None:
    """
    Firebase ID トークンを検証し、デコード済みトークンを返す。

    Returns:
        dict: デコード済みトークン (uid, email, name など)
        None: 検証失敗時
    """
    try:
        app = _get_app()
        decoded = auth.verify_id_token(id_token, app=app)
        return decoded
    except auth.InvalidIdTokenError:
        logger.warning('Invalid Firebase ID token')
    except auth.ExpiredIdTokenError:
        logger.warning('Expired Firebase ID token')
    except auth.RevokedIdTokenError:
        logger.warning('Revoked Firebase ID token')
    except auth.CertificateFetchError:
        logger.error('Firebase certificate fetch error — Firebase が '
                     'プロジェクトで有効か確認してください')
    except Exception:
        logger.exception('Firebase ID token verification failed')
    return None
