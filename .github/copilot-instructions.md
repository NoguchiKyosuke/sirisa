# SIRISA - Copilot Instructions

## プロジェクト概要
SIRISA（学習補助Webサイト）は高校生・教員向けのQ&Aプラットフォームです。
Django 4.2 LTS + PostgreSQL + Celery + Redis で構築されています。

## 技術スタック
- **Backend**: Python 3.12, Django 4.2 LTS
- **Database**: PostgreSQL 16
- **Task Queue**: Celery 5.6 + Redis
- **AI**: Gemini 2.5 Pro (初回回答) + Gemini 2.5 Flash (返信・注釈) / Vertex AI SDK
- **AI制限**: 1アカウント1日100回（`AIUsageLog` モデル）
- **Frontend**: Django Templates + htmx 2.0 + Bootstrap 5.3 + KaTeX
- **認証**: Firebase Authentication（メールリンク + Google サインイン） + Firebase Admin SDK
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
│   ├── accounts/           # 認証（Firebase Auth, カスタムUser, プロフィール, ユーザ通報）
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
- テーマはライトモード固定（ダークモードなし）
- `sanitize_ai_html()` で前処理: DOCTYPE/html/head/body外殻除去 + KaTeX CDN除去 + integrity属性除去 + 未閉じタグ自動閉じ（`<style>`, `<script>` はそのまま維持 — Shadow DOMがCSSを隔離）
- AI回答の `<script>` 内の `document.getElementById` 等はShadow Root経由に自動変換
- Shadow DOM内の `onclick` 属性は `convertOnclickHandlers()` で `addEventListener` に変換。`new Function('event', 'with(window){' + code + '}')` を使用し、(a) `event` パラメータで `currentTarget` アクセス可能、(b) `with(window)` でグローバル関数（`nextSlide_xxx` 等）にアクセス可能。変換は `loadNext` 完了後（=スクリプト読み込み後）に実行。
- Shadow DOM用インラインスクリプト処理で、IIFE内の`function`宣言を自動的に`window`にエクスポート（`window["funcName"]=funcName;` をIIFE末尾に挿入）。これにより`onclick`属性から参照される関数がグローバルスコープで利用可能になる。
- AI返信テキストは `strip_html_document_wrapper()` で `<!DOCTYPE>/<html>/<head>/<body>` 外殻を除去
- 返信エリアの文章選択でも「AIに説明を聞く」ポップアップが使用可能（`reply-body-area` クラス + `data-answer-id`）
- 返信エリア内の数式クリックでも導出過程のAI説明ポップアップが表示される
- 数式クリックハンドラでは `e.stopPropagation()` + `e.preventDefault()` で親要素の onclick（折りたたみ等）が発火しないようにする
- AI回答のプロンプトで「KaTeX数式をonclick属性を持つトリガー要素の内部に配置しない」ルールを追加済み
- Mermaid.jsはShadow DOM内で`mermaid.render()` APIを使って個別レンダリング（startOnLoad不可）
- Mermaid.jsラベル内の丸括弧 `()` と中括弧 `{}` は `sanitizeMermaidCode()` で引用符エスケープ
- AI回答には必ずCSSアニメーション + JSインタラクション + 図/グラフ/ダイアグラムを含める（プロンプトで強制）
- 図表はSVG、Chart.js、Mermaid.js、CSSのみの4方式を教科に応じて使い分け
- AI回答は質問ごとに2種類生成: 「通常」+ 「スライド」（`answer_style` フィールドで区別）。`generate_ai_answer` タスクは両方の pending レコードを先に作成してから生成を開始（ローディングカードが即座に表示されるように）
- **Firebase 認証フロー**: ログインページで Firebase Web SDK（v10 compat）を使い、`signInWithRedirect`（Google）or メールリンク認証 → Firebase ID トークンを `FirebaseCallbackView` に POST → Django セッション作成。新規ユーザは `RegisterView` でユーザ名のみ入力。リダイレクト後は `getRedirectResult()` で結果を処理。
- **Firebase 設定**: `FIREBASE_PROJECT_ID`, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN` を `.env` で管理。`FIREBASE_AUTH_DOMAIN` は自ドメイン（`sirisa.net`）に設定し、Tracking Prevention によるサードパーティストレージブロックを回避。サーバ側は GCE デフォルト認証情報 + Firebase Admin SDK。
- **Firebase nginx プロキシ**: `/__/auth/` と `/__/firebase/` を `sirisa-f5a1f.firebaseapp.com` にリバースプロキシ。`authDomain` を自ドメインにする際に必要（`signInWithRedirect` が `/__/auth/handler` と `/__/firebase/init.json` を参照するため）。
- `User` モデルに `firebase_uid` フィールド（Firebase UID と紐付け）。`FirebaseCallbackView` と `RegisterView` で論理削除済みユーザの `firebase_uid` を自動クリア（IntegrityError 防止）。
- リアクションは👍（いいね）/👎（よくない）の2種類のみ
- 返信はAJAX送信（ページリロードなし）、メディア添付対応（`ReplyMedia`モデル）
- AI返信はポーリングで完了検出（`ReplyStatusAPIView`、4秒間隔）
- ユーザプロフィール: 職業・所属・学年・年齢・自己紹介（`User`モデルに追加フィールド）
- ユーザ通報機能: `UserReport` モデル（24時間に1回制限）
- エクスポート: PDF（WeasyPrint + Noto Sans CJK JP）、Markdown（HTMLテキスト抽出）、CSV/XLSX/TXT
- カスタム右クリックメニュー: 回答エリアでテキスト選択→右クリックで「AIに説明を聞く」（ブラウザデフォルトメニュー非表示）
- SVG内テキストへの注釈: ハイライトはスキップ、ポップアップは表示
- 単語ホバー注釈は文章中の全出現箇所をハイライト（最初の1箇所だけでなく。SVG内テキストは除外）
- 数式クリックポップアップも同じホバー維持挙動（ポップアップ外クリックで消える）
- `max_output_tokens=65536`（Pro）でリッチHTML生成に十分な余地を確保
- ユーザ回答のHTMLは `bleach` でサニタイズ
- ファイルアップロードは100MB制限
- 本番環境は IP 制限あり（Nginx）
- `CSRF_COOKIE_HTTPONLY = True`
## テスト
- `pytest` + `pytest-django` を使用
- テストファイルは各アプリの `tests/` ディレクトリに配置
- ファクトリには `factory_boy` を使用
