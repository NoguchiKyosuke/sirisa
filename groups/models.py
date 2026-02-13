"""
SIRISA グループモデル
少人数グループでの質問共有機能
"""
import uuid
from django.db import models
from django.conf import settings
from core.models import TimeStampMixin


class StudyGroup(TimeStampMixin):
    """学習グループ"""
    name = models.CharField('グループ名', max_length=100)
    description = models.TextField('説明', blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_groups',
        verbose_name='オーナー',
    )
    invite_code = models.CharField(
        '招待コード', max_length=8, unique=True, blank=True,
    )
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        verbose_name = 'グループ'
        verbose_name_plural = 'グループ'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)


class GroupMembership(TimeStampMixin):
    """グループメンバーシップ"""

    class Role(models.TextChoices):
        OWNER = 'owner', 'オーナー'
        MEMBER = 'member', 'メンバー'

    group = models.ForeignKey(
        StudyGroup, on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='グループ',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        verbose_name='ユーザ',
    )
    role = models.CharField(
        '役割', max_length=10,
        choices=Role.choices, default=Role.MEMBER,
    )

    class Meta:
        verbose_name = 'グループメンバー'
        verbose_name_plural = 'グループメンバー'
        unique_together = ['group', 'user']

    def __str__(self):
        return f'{self.user.username} @ {self.group.name}'
