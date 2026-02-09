---
applyTo: "**/tasks.py"
---

# Celery Tasks ガイドライン

## 設定
- Broker: Redis (`redis://127.0.0.1:6379/0`)
- Backend: Redis (`redis://127.0.0.1:6379/1`)
- シリアライザ: JSON
- タイムゾーン: Asia/Tokyo

## タスク定義
```python
from celery import shared_task

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def my_task(self, arg1, arg2):
    try:
        # 処理
        pass
    except Exception as exc:
        self.retry(exc=exc)
```

## 規約
- `@shared_task` デコレータを使用（プロジェクト依存を避ける）
- `bind=True` でタスクインスタンスにアクセス
- リトライ: `max_retries=3`, `default_retry_delay=30`
- ログ: `logging.getLogger(__name__)` を使用
- DB 操作時は最新のオブジェクトを取得（`refresh_from_db`）

## AI 回答生成タスク
- `generate_ai_answer(question_id)` が主要タスク
- Answer レコードを `pending` で作成 → Gemini 呼出 → `completed` / `failed` に更新
- フロントエンドは htmx ポーリング (`every 5s`) でステータス確認
