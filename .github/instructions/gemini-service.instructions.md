---
applyTo: "**/services/gemini_service.py,**/services/prompts.py"
---

# Gemini AI サービス ガイドライン

## SDK
- `google-generativeai` パッケージを使用
- モデル: `gemini-2.0-flash`
- API キー: `settings.GEMINI_API_KEY`（.env から読み込み）

## プロンプト設計
- `prompts.py` に `BASE_PROMPT` と `SUBJECT_PROMPTS` を定義
- 教科別プロンプトで専門的な回答を生成
- ベースプロンプト: 高校生向け、日本語、段階的説明、KaTeX数式対応

## 出力処理
- 生成テキストは `bleach.clean()` でサニタイズ
- 許可タグ: p, br, strong, em, ul, ol, li, code, pre, h3, h4, h5, blockquote, span, div, sub, sup, table, thead, tbody, tr, th, td
- 許可属性: class（KaTeX用）
- Markdown → HTML 変換は `markdown` ライブラリ + `fenced_code`, `tables` 拡張

## エラーハンドリング
- API キー未設定: ログ警告して空文字返却
- API エラー: 例外を raise してCeleryタスク側でリトライ
- レート制限: Celery のリトライ機構で対応

## セキュリティ
- API キーはコードにハードコードしない
- ユーザー入力をプロンプトに含める際は適切にエスケープ
- 生成結果は必ずサニタイズしてから保存
