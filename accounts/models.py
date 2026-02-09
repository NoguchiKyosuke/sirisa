"""
SIRISA アカウントモデル
カスタムユーザ、メール認証
"""
import random
import string
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'ユーザ'
        verbose_name_plural = 'ユーザ'

    def __str__(self):
        return self.username


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
