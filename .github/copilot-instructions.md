# SIRISA - Copilot Instructions

## プロジェクト概要
SIRISA（学習補助Webサイト）は高校生・教員向けのQ&Aプラットフォームです。
Django 4.2 LTS + PostgreSQL + Celery + Redis で構築されています。

## 技術スタック
- **Backend**: Python 3.12, Django 4.2 LTS
- **Database**: PostgreSQL 16
- **Task Queue**: Celery 5.6 + Redis
- **AI**: Google Gemini 2.0 Flash (Vertex AI / google-cloud-aiplatform SDK)
- **AI制限**: 1アカウント1日100回（`AIUsageLog` モデル）
- **Frontend**: Django Templates + htmx 2.0 + Bootstrap 5.3 + KaTeX
- **Server**: Nginx + Gunicorn (systemd)

## ディレクトリ構成
```
/opt/sirisa/
├── .env                    # 環境変数（SECRET_KEY, DB, API keys）
├── venv/                   # Python仮想環境
├── logs/                   # アプリログ
├── src/                    # ソースコード (git root)
│   ├── sirisa_project/     # Djangoプロジェクト設定
│   │   ├── settings/       # base.py, development.py, production.py
│   │   ├── celery.py       # Celeryアプリ設定
│   │   └── urls.py
│   ├── core/               # 共通モデル（SoftDelete, TimeStamp, DeletionLog）
│   ├── accounts/           # 認証（カスタムUser, パスワードレス認証）
│   ├── questions/          # 質問・回答・リアクション・返信・AI注釈・エクスポート
│   │   ├── services/       # Gemini AI, プロンプト
│   │   ├── fixtures/       # subjects.json (教科マスタ)
│   │   └── export.py       # CSV/XLSX/PDF/MD/TXT
│   ├── content/            # サンドボックスiframe配信 (content.sirisa.net)
│   ├── groups/             # 学習グループ（招待コード、メンバー管理）
│   ├── pages/              # 静的ページ（FAQ, 利用規約, プライバシー等）
│   ├── templates/          # グローバルテンプレート (base.html, 404, 500)
│   └── requirements.txt
```

## 言語とロケール
- UIテキストは **日本語** で記述
- コード内のコメントは日本語OK
- 変数名・関数名・クラス名は **英語**
- コミットメッセージは `[AI]` プレフィックス + 日本語

## コーディング規約
- PEP 8 準拠、行長 99 文字
- Django Class-Based Views 優先
- モデルは `TimeStampMixin` と `SoftDeleteMixin` を継承（物理削除禁止）
- テンプレートは `{% extends 'base.html' %}` を使用
- htmx で部分更新する場合は partials/ ディレクトリのテンプレートを使用
- フォームには Bootstrap 5 クラスを付与

## セキュリティ
- IP制限によりアクセス可能なユーザが限定されているため、HTML出力に制限なし
- AI回答はShadow DOM内に表示（CSS/JSがページ全体に影響しない）
- `sanitize_ai_html()` で前処理: DOCTYPE/html/head/body外殻除去 + KaTeX CDN除去 + integrity属性除去 + 未閉じタグ自動閉じ（`<style>`, `<script>` はそのまま維持 — Shadow DOMがCSSを隔離）
- AI回答の `<script>` 内の `document.getElementById` 等はShadow Root経由に自動変換
- Mermaid.jsはShadow DOM内で`mermaid.render()` APIを使って個別レンダリング（startOnLoad不可）
- AI回答には必ずCSSアニメーション + JSインタラクション + 図/グラフ/ダイアグラムを含める（プロンプトで強制）
- 図表はSVG、Chart.js、Mermaid.js、CSSのみの4方式を教科に応じて使い分け
- AI回答は質問ごとに2種類生成: 「通常」+ 「スライド」（`answer_style` フィールドで区別）
- 単語ホバー注釈は文章中の全出現箇所をハイライト（最初の1箇所だけでなく）
- 注釈ポップアップはトリガー要素またはポップアップ上にカーソルがある間は表示維持、他の場所に触れると消える
- 数式クリックポップアップも同じホバー維持挙動（ポップアップ外クリックで消える）
- `max_output_tokens=16384`でリッチHTML生成に十分な余地を確保
- ユーザ回答のHTMLは `bleach` でサニタイズ
- ファイルアップロードは100MB制限
- 本番環境は IP 制限あり（Nginx）
- `CSRF_COOKIE_HTTPONLY = True`
## テスト
- `pytest` + `pytest-django` を使用
- テストファイルは各アプリの `tests/` ディレクトリに配置
- ファクトリには `factory_boy` を使用
