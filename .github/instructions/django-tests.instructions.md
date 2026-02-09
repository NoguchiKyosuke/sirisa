---
applyTo: "**/tests/**"
---

# テスト ガイドライン

## フレームワーク
- `pytest` + `pytest-django` を使用
- `conftest.py` に共通フィクスチャを配置
- `factory_boy` でテストデータ生成

## ファイル構成
```
app/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # アプリ固有フィクスチャ
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_forms.py
│   └── test_services.py     # 外部サービス連携テスト
```

## 命名規約
- テストファイル: `test_*.py`
- テストクラス: `Test<対象クラス名>`
- テストメソッド: `test_<動作の説明>`

## 原則
- 外部 API (Gemini, Gmail) は `unittest.mock.patch` でモック
- DB アクセスには `@pytest.mark.django_db` を付与
- ソフトデリートのテスト: 削除後に `objects` で取得不可、`all_with_deleted()` で取得可能を確認
- htmx リクエストのテスト: `HTTP_HX_REQUEST='true'` ヘッダーを設定
