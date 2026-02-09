---
applyTo: "**/models.py"
---

# Django Models ガイドライン

## 必須ルール
- 全モデルは `core.models.TimeStampMixin` を継承すること（created_at, updated_at 自動付与）
- 削除が必要なモデルは `core.models.SoftDeleteMixin` も継承（物理削除禁止）
- SoftDeleteMixin使用時は `objects = SoftDeleteManager()` を設定
- `__str__` メソッドを必ず実装
- `class Meta` に `ordering` と `verbose_name` / `verbose_name_plural` を設定

## ソフトデリート
```python
from core.models import TimeStampMixin, SoftDeleteMixin, SoftDeleteManager

class MyModel(TimeStampMixin, SoftDeleteMixin, models.Model):
    objects = SoftDeleteManager()
    # ...
    def soft_delete(self, user=None):
        super().soft_delete(user)  # DeletionLog が自動生成される
```

## フィールド規約
- CharField: `max_length` を必ず指定
- ForeignKey: `on_delete` を明示、`related_name` を設定
- ファイルフィールド: `upload_to` にモデル名を含むパスを指定
- choices はモデルクラス内に定数として定義

## 例
```python
class Question(TimeStampMixin, SoftDeleteMixin, models.Model):
    BODY_FORMAT_CHOICES = [
        ('html', 'HTML'),
        ('markdown', 'Markdown'),
        ('text', 'プレーンテキスト'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField('タイトル', max_length=200)
    objects = SoftDeleteManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = '質問'
        verbose_name_plural = '質問'
```
