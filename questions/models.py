"""
SIRISA 質問・回答モデル
"""
import os
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from core.models import TimeStampMixin, SoftDeleteMixin, SoftDeleteManager


class Subject(models.Model):
    """教科マスタ"""
    name = models.CharField('教科名', max_length=50, unique=True)
    is_custom = models.BooleanField('カスタム教科', default=False)
    is_deleted = models.BooleanField('削除済み', default=False)
    order = models.IntegerField('表示順', default=0)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = '教科'
        verbose_name_plural = '教科'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Question(TimeStampMixin, SoftDeleteMixin):
    """質問モデル"""

    class BodyFormat(models.TextChoices):
        HTML = 'html', 'HTML'
        MARKDOWN = 'markdown', 'Markdown'
        TEXT = 'text', 'テキスト'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='questions',
        verbose_name='質問者',
    )
    title = models.CharField('質問タイトル', max_length=200)
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT,
        related_name='questions',
        verbose_name='教科',
    )
    custom_subject = models.CharField(
        'カスタム教科名', max_length=50, blank=True,
        help_text='「その他」選択時に入力',
    )
    body = models.TextField('本文')
    body_format = models.CharField(
        '本文フォーマット', max_length=10,
        choices=BodyFormat.choices, default=BodyFormat.TEXT,
    )
    is_resolved = models.BooleanField('解決済み', default=False)

    # グループ共有: Noneなら全体公開
    group = models.ForeignKey(
        'groups.StudyGroup', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='questions',
        verbose_name='共有グループ',
    )
    visibility = models.CharField(
        '公開範囲', max_length=10,
        choices=[('public', '全体公開'), ('group', 'グループ内')],
        default='public',
    )

    class Meta:
        verbose_name = '質問'
        verbose_name_plural = '質問'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    @property
    def display_subject(self):
        """表示用教科名"""
        if self.subject.name == 'その他' and self.custom_subject:
            return self.custom_subject
        return self.subject.name

    @property
    def total_media_size(self):
        """添付ファイル合計サイズ（バイト）"""
        return sum(m.file_size for m in self.media_files.filter(is_deleted=False))


def question_media_path(instance, filename):
    """質問メディアファイルのアップロードパス"""
    return f'questions/{instance.question.pk}/{filename}'


class QuestionMedia(TimeStampMixin, SoftDeleteMixin):
    """質問添付メディア"""

    class MediaType(models.TextChoices):
        IMAGE = 'image', '画像'
        AUDIO = 'audio', '音声'
        VIDEO = 'video', '動画'
        OTHER = 'other', 'その他'

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='media_files',
        verbose_name='質問',
    )
    file = models.FileField(
        'ファイル', upload_to=question_media_path,
        validators=[FileExtensionValidator(
            allowed_extensions=[
                'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
                'mp3', 'wav', 'ogg', 'm4a',
                'mp4', 'webm', 'mov', 'avi',
                'pdf', 'doc', 'docx', 'txt',
            ]
        )],
    )
    media_type = models.CharField(
        'メディア種別', max_length=10,
        choices=MediaType.choices, default=MediaType.OTHER,
    )
    file_size = models.PositiveIntegerField('ファイルサイズ（バイト）', default=0)
    original_name = models.CharField('元ファイル名', max_length=255, blank=True)

    class Meta:
        verbose_name = '質問メディア'
        verbose_name_plural = '質問メディア'

    def __str__(self):
        return self.original_name or os.path.basename(self.file.name)

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if not self.original_name and self.file:
            self.original_name = os.path.basename(self.file.name)
        if not self.media_type or self.media_type == self.MediaType.OTHER:
            self.media_type = self._detect_media_type()
        super().save(*args, **kwargs)

    def _detect_media_type(self):
        """ファイル拡張子からメディア種別を判定"""
        if not self.file:
            return self.MediaType.OTHER
        ext = os.path.splitext(self.file.name)[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'):
            return self.MediaType.IMAGE
        elif ext in ('.mp3', '.wav', '.ogg', '.m4a'):
            return self.MediaType.AUDIO
        elif ext in ('.mp4', '.webm', '.mov', '.avi'):
            return self.MediaType.VIDEO
        return self.MediaType.OTHER


class Answer(TimeStampMixin, SoftDeleteMixin):
    """回答モデル"""

    class BodyFormat(models.TextChoices):
        HTML = 'html', 'HTML'
        MARKDOWN = 'markdown', 'Markdown'
        TEXT = 'text', 'テキスト'

    class AIStatus(models.TextChoices):
        NONE = 'none', '対象外'
        PENDING = 'pending', '生成中'
        COMPLETED = 'completed', '完了'
        FAILED = 'failed', '失敗'

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='質問',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='answers',
        verbose_name='回答者',
    )
    body = models.TextField('回答本文')
    body_format = models.CharField(
        '本文フォーマット', max_length=10,
        choices=BodyFormat.choices, default=BodyFormat.TEXT,
    )
    is_ai_generated = models.BooleanField('AI生成', default=False)
    ai_model = models.CharField('AIモデル', max_length=50, blank=True)
    ai_generation_status = models.CharField(
        'AI生成ステータス', max_length=10,
        choices=AIStatus.choices, default=AIStatus.NONE,
    )

    class Meta:
        verbose_name = '回答'
        verbose_name_plural = '回答'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.question.title} への回答 by {self.user.username}'

    @property
    def reaction_score(self):
        """リアクションスコア（ソート用）"""
        positive = self.reactions.filter(
            emoji_type__in=['thumbs_up', 'heart', 'celebration', 'idea']
        ).count()
        negative = self.reactions.filter(emoji_type='thumbs_down').count()
        return positive - negative


def answer_media_path(instance, filename):
    """回答メディアファイルのアップロードパス"""
    return f'answers/{instance.answer.pk}/{filename}'


class AnswerMedia(TimeStampMixin, SoftDeleteMixin):
    """回答添付メディア"""

    class MediaType(models.TextChoices):
        IMAGE = 'image', '画像'
        AUDIO = 'audio', '音声'
        VIDEO = 'video', '動画'
        OTHER = 'other', 'その他'

    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE,
        related_name='media_files',
        verbose_name='回答',
    )
    file = models.FileField(
        'ファイル', upload_to=answer_media_path,
        validators=[FileExtensionValidator(
            allowed_extensions=[
                'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
                'mp3', 'wav', 'ogg', 'm4a',
                'mp4', 'webm', 'mov', 'avi',
                'pdf', 'doc', 'docx', 'txt',
            ]
        )],
    )
    media_type = models.CharField(
        'メディア種別', max_length=10,
        choices=MediaType.choices, default=MediaType.OTHER,
    )
    file_size = models.PositiveIntegerField('ファイルサイズ（バイト）', default=0)
    original_name = models.CharField('元ファイル名', max_length=255, blank=True)

    class Meta:
        verbose_name = '回答メディア'
        verbose_name_plural = '回答メディア'

    def __str__(self):
        return self.original_name or os.path.basename(self.file.name)


class Reaction(models.Model):
    """リアクションモデル（5種類の絵文字）"""

    class EmojiType(models.TextChoices):
        THUMBS_UP = 'thumbs_up', '👍'
        THUMBS_DOWN = 'thumbs_down', '👎'
        HEART = 'heart', '❤️'
        CELEBRATION = 'celebration', '🎉'
        IDEA = 'idea', '💡'

    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='回答',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reactions',
        verbose_name='ユーザ',
    )
    emoji_type = models.CharField(
        '絵文字種別', max_length=20,
        choices=EmojiType.choices,
    )
    created_at = models.DateTimeField('作成日時', auto_now_add=True)

    class Meta:
        verbose_name = 'リアクション'
        verbose_name_plural = 'リアクション'
        unique_together = ['answer', 'user', 'emoji_type']

    def __str__(self):
        return f'{self.get_emoji_type_display()} by {self.user.username}'


class QuestionDraft(models.Model):
    """質問下書き（自動保存用）"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='question_drafts',
        verbose_name='ユーザ',
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='drafts',
        verbose_name='対象質問',
    )
    title = models.CharField('タイトル', max_length=200, blank=True)
    subject_id = models.IntegerField('教科ID', null=True, blank=True)
    custom_subject = models.CharField('カスタム教科', max_length=50, blank=True)
    body = models.TextField('本文', blank=True)
    body_format = models.CharField('フォーマット', max_length=10, blank=True)
    auto_saved_at = models.DateTimeField('自動保存日時', auto_now=True)

    class Meta:
        verbose_name = '質問下書き'
        verbose_name_plural = '質問下書き'

    def __str__(self):
        return f'{self.user.username} の下書き: {self.title}'


class AnswerDraft(models.Model):
    """回答下書き（自動保存用）"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='answer_drafts',
        verbose_name='ユーザ',
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='answer_drafts',
        verbose_name='対象質問',
    )
    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='drafts',
        verbose_name='対象回答',
    )
    body = models.TextField('本文', blank=True)
    body_format = models.CharField('フォーマット', max_length=10, blank=True)
    auto_saved_at = models.DateTimeField('自動保存日時', auto_now=True)

    class Meta:
        verbose_name = '回答下書き'
        verbose_name_plural = '回答下書き'

    def __str__(self):
        return f'{self.user.username} の回答下書き'


class Reply(TimeStampMixin, SoftDeleteMixin):
    """回答への返信モデル"""

    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='回答',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='replies',
        verbose_name='返信者',
    )
    body = models.TextField('返信本文')
    is_ai_generated = models.BooleanField('AI生成', default=False)
    ai_model = models.CharField('AIモデル', max_length=50, blank=True)
    ai_generation_status = models.CharField(
        'AI生成ステータス', max_length=10,
        choices=Answer.AIStatus.choices, default=Answer.AIStatus.NONE,
    )

    class Meta:
        verbose_name = '返信'
        verbose_name_plural = '返信'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.answer} への返信 by {self.user.username}'


class AIAnnotation(TimeStampMixin):
    """AIによる補足注釈（数式導出・単語説明）"""

    class AnnotationType(models.TextChoices):
        FORMULA = 'formula', '数式導出'
        WORD = 'word', '単語説明'
        SUPPLEMENT = 'supplement', '補完情報'

    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE,
        related_name='annotations',
        verbose_name='回答',
    )
    annotation_type = models.CharField(
        '注釈種別', max_length=20,
        choices=AnnotationType.choices,
    )
    selected_text = models.TextField('選択テキスト')
    context_before = models.TextField('前文脈', blank=True)
    context_after = models.TextField('後文脈', blank=True)
    explanation = models.TextField('AI説明（Markdown）')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='annotations',
        verbose_name='作成者',
    )

    class Meta:
        verbose_name = 'AI注釈'
        verbose_name_plural = 'AI注釈'

    def __str__(self):
        return f'{self.annotation_type}: {self.selected_text[:30]}'

