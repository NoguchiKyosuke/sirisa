"""
SIRISA アカウントモデル
カスタムユーザ、メール認証
"""
import random
import string
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """カスタムユーザモデル"""

    class Role(models.TextChoices):
        STUDENT = 'student', '生徒'
        TEACHER = 'teacher', '教師'
        AI_AGENT = 'ai_agent', 'AIエージェント'

    email = models.EmailField('メールアドレス', unique=True)
    role = models.CharField(
        'ロール', max_length=20,
        choices=Role.choices, default=Role.STUDENT,
    )
    is_verified = models.BooleanField('メール認証済み', default=False)
    is_deleted = models.BooleanField('削除済み', default=False)
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    original_email = models.EmailField('削除前メールアドレス', blank=True, default='')
    original_username = models.CharField('削除前ユーザ名', max_length=150, blank=True, default='')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'ユーザ'
        verbose_name_plural = 'ユーザ'

    def __str__(self):
        return self.original_username if self.is_deleted else self.username

    def anonymize_for_deletion(self):
        """削除時にemail/usernameを匿名化して一意制約を解放する"""
        suffix = uuid.uuid4().hex[:12]
        self.original_email = self.email
        self.original_username = self.username
        self.email = f'deleted_{suffix}@deleted.local'
        self.username = f'deleted_{suffix}'
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()


class EmailVerification(models.Model):
    """メール認証コードモデル"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='verifications',
        verbose_name='ユーザ',
    )
    code = models.CharField('認証コード', max_length=6)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    expires_at = models.DateTimeField('有効期限')
    is_used = models.BooleanField('使用済み', default=False)

    class Meta:
        verbose_name = 'メール認証'
        verbose_name_plural = 'メール認証'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.code}'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.digits, k=6))
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """有効期限切れかどうか"""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """有効かどうか（未使用かつ期限内）"""
        return not self.is_used and not self.is_expired
