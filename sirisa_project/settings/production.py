"""
SIRISA 本番環境設定
"""
from .base import *  # noqa: F401,F403

DEBUG = False

# 本番ではCSRF設定を適切に
CSRF_TRUSTED_ORIGINS = [
    'http://34.28.25.207',
]

# セキュリティ設定
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
