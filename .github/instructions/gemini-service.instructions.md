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
- プロンプトに具体的なアニメーションコード例を記載し、Geminiが必ず実装するよう強制
- `max_output_tokens=16384`（リッチHTML生成のため十分なトークン量を確保）

## 出力処理
- AI回答・返信・注釈はすべてHTML形式で出力（Markdown不可）
- AI回答はそのままDBに保存（コードフェンス除去のみ）
- 表示時に `sanitize_ai_html()` で前処理: 未閉じタグ自動閉じ + integrity属性除去（`<style>`, `<script>` はそのまま維持）
- AI回答はShadow DOM内に表示（CSS/JSがページ全体に影響しない）
- AI回答内の `document.getElementById` 等はShadow Root経由に自動変換される
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
