"""
SIRISA プロジェクト共通設定
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / '.env')

# プロジェクトのベースディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# セキュリティキー
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')

# デバッグモード（デフォルトFalse）
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

# 許可ホスト
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h.strip()]

# アプリケーション定義
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # サードパーティ
    'django_htmx',
    'django_cleanup.apps.CleanupConfig',
    # 自作アプリ
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'questions.apps.QuestionsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'sirisa_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sirisa_project.wsgi.application'

# データベース設定
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'sirisa_db'),
        'USER': os.getenv('DB_USER', 'sirisa_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# パスワードバリデーション
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# カスタムユーザモデル
AUTH_USER_MODEL = 'accounts.User'

# 認証リダイレクト
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# 国際化設定
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# 静的ファイル
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = Path(__file__).resolve().parent.parent.parent.parent / 'staticfiles'

# メディアファイル
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent.parent / 'media'

# アップロードサイズ上限（110MB）
FILE_UPLOAD_MAX_MEMORY_SIZE = 115343360
DATA_UPLOAD_MAX_MEMORY_SIZE = 115343360

# セッション設定（30日間保持＝自動ログイン）
SESSION_COOKIE_AGE = 2592000  # 30日
SESSION_SAVE_EVERY_REQUEST = True

# デフォルト主キー
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery設定
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tokyo'

# Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Gmail API
GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', '')
GMAIL_TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', '')
GMAIL_SENDER_EMAIL = os.getenv('GMAIL_SENDER_EMAIL', 'ryotatakahashi0123@gmail.com')

# ログ設定
LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'django.log',
            'formatter': 'verbose',
        },
        'deletion_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'deletion.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'deletion': {
            'handlers': ['deletion_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'gemini': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
