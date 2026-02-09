---
applyTo: "**/templates/**"
---

# Django Templates ガイドライン

## 構成
- `templates/base.html` がグローバルベーステンプレート
- 各アプリ: `app/templates/app/xxx.html`
- 部分テンプレート: `app/templates/app/partials/xxx.html`

## 必須ブロック
```html
{% extends 'base.html' %}
{% block title %}ページタイトル{% endblock %}
{% block content %}
  <!-- メインコンテンツ -->
{% endblock %}
{% block extra_js %}
  <!-- ページ固有のJS -->
{% endblock %}
```

## htmx 統合
- 部分更新: `hx-get`, `hx-post`, `hx-target`, `hx-swap`
- ポーリング: `hx-trigger="every Ns"`
- htmx レスポンス用テンプレートは `partials/` に配置
- CSRF: `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`

## UI フレームワーク
- Bootstrap 5.3 クラスを使用
- カスタムクラス: `.btn-sirisa` (プライマリボタン), `.card` (コンテンツカード)
- レスポンシブ: `col-lg-*`, `col-md-*` でブレークポイント対応
- アイコン: Bootstrap Icons (`bi bi-xxx`)

## 日本語テキスト
- UI テキストはすべて日本語
- 日付フォーマット: `{{ date|date:"Y-m-d H:i" }}`

## 数式表示
- KaTeX を使用: `$...$`（インライン）, `$$...$$`（ブロック）
- base.html に KaTeX CDN を読み込み済み
