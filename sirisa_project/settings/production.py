"""
SIRISA 本番環境設定
"""
from .base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = ['sirisa.net', 'www.sirisa.net', 'content.sirisa.net', '34.28.41.172', 'localhost', '127.0.0.1']

# 本番ではCSRF設定を適切に
CSRF_TRUSTED_ORIGINS = [
    'https://sirisa.net',
    'https://www.sirisa.net',
    'https://content.sirisa.net',
    'http://34.28.41.172',
]

# セキュリティ設定
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# コンテンツサブドメイン設定
CONTENT_DOMAIN = 'content.sirisa.net'
