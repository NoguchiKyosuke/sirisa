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
- プロンプトで `<style>`, `<script>`, `<svg>` の使用を推奨（CSSアニメーション、SVG図形、JSインタラクション）

## 出力処理
- AI回答はサニタイズせずそのままDBに保存（コードフェンス除去のみ）
- セキュリティは content.sirisa.net のサンドボックスiframe（sandbox="allow-scripts"）で確保
- ユーザ回答は従来通り `bleach.clean()` でサニタイズ

## エラーハンドリング
- API キー未設定: ログ警告して空文字返却
- API エラー: 例外を raise してCeleryタスク側でリトライ
- レート制限: Celery のリトライ機構で対応

## セキュリティ
- API キーはコードにハードコードしない
- ユーザー入力をプロンプトに含める際は適切にエスケープ
- AI生成結果はサニタイズせず保存し、サンドボックスiframeで隔離表示する
- ユーザ回答は `bleach` でサニタイズしてから保存
