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
    firebase_uid = models.CharField(
        'Firebase UID', max_length=128,
        unique=True, null=True, blank=True,
        help_text='Firebase Authentication のユーザ UID',
    )
    role = models.CharField(
        'ロール', max_length=20,
        choices=Role.choices, default=Role.STUDENT,
    )
    is_verified = models.BooleanField('メール認証済み', default=False)
    is_deleted = models.BooleanField('削除済み', default=False)
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    original_email = models.EmailField('削除前メールアドレス', blank=True, default='')
    original_username = models.CharField('削除前ユーザ名', max_length=150, blank=True, default='')

    # プロフィール情報
    occupation = models.CharField('職業・身分', max_length=100, blank=True,
                                  help_text='例: 高校生、大学生、会社員、教師')
    workplace_school = models.CharField('所属（学校・職場）', max_length=200, blank=True,
                                        help_text='例: ○○高校、△△大学')
    grade = models.CharField('学年・役職', max_length=50, blank=True,
                             help_text='例: 高校2年、学部3年、主任')
    age = models.PositiveIntegerField('年齢', null=True, blank=True)
    bio = models.TextField('自己紹介', max_length=500, blank=True)

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


class UserReport(models.Model):
    """ユーザ通報モデル"""

    class Reason(models.TextChoices):
        SPAM = 'spam', 'スパム・迷惑行為'
        INAPPROPRIATE = 'inappropriate', '不適切なコンテンツ'
        HARASSMENT = 'harassment', '嫌がらせ'
        IMPERSONATION = 'impersonation', 'なりすまし'
        OTHER = 'other', 'その他'

    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name='通報者',
    )
    reported_user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='reports_received',
        verbose_name='被通報ユーザ',
    )
    reason = models.CharField(
        '通報理由', max_length=20,
        choices=Reason.choices,
    )
    detail = models.TextField('詳細', max_length=500, blank=True)
    created_at = models.DateTimeField('通報日時', auto_now_add=True)
    is_resolved = models.BooleanField('対応済み', default=False)

    class Meta:
        verbose_name = 'ユーザ通報'
        verbose_name_plural = 'ユーザ通報'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reporter.username} → {self.reported_user.username}: {self.get_reason_display()}'
