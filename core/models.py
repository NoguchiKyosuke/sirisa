"""
SIRISA 共通モデル
論理削除ミックスイン、タイムスタンプミックスイン、削除ログ
"""
import logging
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

deletion_logger = logging.getLogger('deletion')


class SoftDeleteManager(models.Manager):
    """論理削除されていないレコードのみ返すマネージャ"""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """論理削除済みを含む全レコードを返す"""
        return super().get_queryset()

    def deleted_only(self):
        """論理削除済みのレコードのみ返す"""
        return super().get_queryset().filter(is_deleted=True)


class TimeStampMixin(models.Model):
    """作成日時・更新日時の共通フィールド"""
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """論理削除ミックスイン"""
    is_deleted = models.BooleanField('削除済み', default=False, db_index=True)
    deleted_at = models.DateTimeField('削除日時', null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='削除実行者',
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None, description=''):
        """論理削除を実行し、削除ログを記録する"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

        # 削除ログをDBに記録
        DeletionLog.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.pk,
            description=description or f'{self.__class__.__name__} (ID: {self.pk}) を削除',
        )

        # サーバログにも記録
        user_name = user.username if user else '不明'
        deletion_logger.info(
            f'論理削除: {self.__class__.__name__} ID={self.pk} '
            f'by {user_name} - {description}'
        )

    def restore(self):
        """論理削除を復元する"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class DeletionLog(models.Model):
    """削除操作のログ"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='削除実行者',
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='対象モデル',
    )
    object_id = models.PositiveIntegerField('対象ID')
    content_object = GenericForeignKey('content_type', 'object_id')
    description = models.TextField('説明', blank=True)
    deleted_at = models.DateTimeField('削除日時', auto_now_add=True)

    class Meta:
        verbose_name = '削除ログ'
        verbose_name_plural = '削除ログ'
        ordering = ['-deleted_at']

    def __str__(self):
        return f'{self.deleted_at} - {self.description}'
