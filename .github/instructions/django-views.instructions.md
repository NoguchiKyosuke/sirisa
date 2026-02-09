---
applyTo: "**/views.py"
---

# Django Views ガイドライン

## 基本方針
- Class-Based Views (CBV) を優先的に使用
- `LoginRequiredMixin` を認証が必要なビューに適用
- htmx リクエスト判定: `request.htmx` (django-htmx ミドルウェア)
- htmx の場合は partials テンプレートを返す

## パターン
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

class MyView(LoginRequiredMixin, View):
    def get(self, request):
        # htmx判定
        template = 'app/partials/my_partial.html' if request.htmx else 'app/my_page.html'
        return render(request, template, context)
```

## API エンドポイント
- JSON レスポンスには `JsonResponse` を使用
- POST のみ受け付ける API は `require_POST` デコレータまたは `View` で `post` メソッドのみ実装
- エラーは適切な HTTP ステータスコードで返す

## エラーハンドリング
- `get_object_or_404()` を使用
- ソフトデリート対象は `objects` マネージャー経由（削除済みは自動除外）
- 権限チェック: オブジェクトの所有者確認を行う

## ページネーション
- `django.core.paginator.Paginator` を使用
- デフォルト 20 件/ページ
- htmx リクエスト時はページ部分のみ返す
