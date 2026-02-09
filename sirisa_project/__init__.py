"""
SIRISA プロジェクト初期化
Celeryアプリをロードする
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
