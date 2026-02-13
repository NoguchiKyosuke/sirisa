---
applyTo: "**/services/gemini_service.py,**/services/prompts.py"
---

# Gemini AI サービス ガイドライン

## SDK
- `google-generativeai` パッケージを使用
- モデル: `gemini-2.0-flash`
- API キー: `settings.GCLOUD_API_KEY`（.env から読み込み）

## プロンプト設計
- `prompts.py` に `BASE_PROMPT` と `SUBJECT_PROMPTS` を定義
- 教科別プロンプトで専門的な回答を生成
- ベースプロンプト: 高校生向け、日本語、段階的説明、KaTeX数式対応
- **アニメーション必須**: CSSアニメーション（@keyframes fadeSlideIn等）+ JSインタラクション（クリック展開等）を毎回含める
- **図・グラフ必須**: SVG、Chart.js、Mermaid.js等を使い最低1つの図・グラフ・ダイアグラムを含める
- プロンプトに具体的なアニメーション・図表コード例を記載し、Geminiが必ず実装するよう強制
- 使い分け: 数学グラフ→SVG, 統計データ→Chart.js, フロー→Mermaid.js, タイムライン→CSS+SVG
- `max_output_tokens=16384`（リッチHTML生成のため十分なトークン量を確保）
- 質問ごとに2種類のAI回答を生成: `normal`（通常）+ `slide`（スライドプレゼン形式）
- `SLIDE_PROMPT` でスライド形式の出力を定義（ナビゲーション付きプレゼンHTML）
- `generate_answer()` に `style` 引数: 'normal' or 'slide' でプロンプト切替

## 出力処理
- AI回答・返信・注釈はすべてHTML形式で出力（Markdown不可）
- AI回答はそのままDBに保存（コードフェンス除去のみ）
- 表示時に `sanitize_ai_html()` で前処理:
  - `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` の外殻タグ除去（Shadow DOM内に配置するため完全なHTML文書不要）
  - `<meta>`, `<title>` タグ除去（不要）
  - KaTeX CDNリンク/スクリプト除去（Shadow DOM側で既に読み込み済み）
  - `integrity`/`crossorigin` 属性除去（Geminiの不正ハッシュ防止）
  - 未閉じタグ自動閉じ
  - `<style>`, `<script>` はそのまま維持
- AI回答はShadow DOM内に表示（CSS/JSがページ全体に影響しない）
- AI回答内の `document.getElementById` 等はShadow Root経由に自動変換される
- Mermaid.jsはShadow DOM内では`mermaid.render()` APIを使って個別レンダリング（startOnLoadは動作しない）
- KaTeX CSSはShadow DOM内に別途読み込み
- ユーザ回答は従来通り `bleach.clean()` でサニタイズ

## エラーハンドリング
- API キー未設定: ログ警告して空文字返却
- API エラー: 例外を raise してCeleryタスク側でリトライ
- レート制限: Celery のリトライ機構で対応

## セキュリティ
- API キーはコードにハードコードしない
- ユーザー入力をプロンプトに含める際は適切にエスケープ
- AI生成結果は保存後、表示時に `sanitize_ai_html()` で前処理（タグ閉じ・integrity除去のみ。script/styleは除去しない）
- AI回答はShadow DOMで表示されるため、CSS/JSはページ全体に影響しない
- ユーザ回答は `bleach` でサニタイズしてから保存
