"""
SIRISA Gemini APIサービス (Vertex AI)
質問に対するAI回答を生成する
"""
import re
import logging
import bleach
from django.conf import settings

logger = logging.getLogger('gemini')

# Vertex AI設定
VERTEX_PROJECT = 'sirisa'
VERTEX_LOCATION = 'us-central1'
# Pro: 初回回答（高品質）、Flash: 返信・注釈・補完（高速）
VERTEX_MODEL_PRO = 'gemini-2.5-pro'
VERTEX_MODEL_FLASH = 'gemini-2.5-flash'

# bleachで許可するHTMLタグと属性
ALLOWED_TAGS = [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'strong', 'em', 'b', 'i',
    'code', 'pre', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
    'br', 'hr', 'blockquote', 'span', 'div',
    'a', 'sup', 'sub', 'dl', 'dt', 'dd',
    'caption', 'colgroup', 'col', 'details', 'summary',
    'figure', 'figcaption', 'mark', 'small', 'abbr',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style'],
    'a': ['href', 'title'],
    'th': ['colspan', 'rowspan', 'scope'],
    'td': ['colspan', 'rowspan'],
    'col': ['span'],
    'abbr': ['title'],
}

# 許可するCSSプロパティ
ALLOWED_STYLES = [
    'color', 'background-color', 'background', 'border', 'border-radius',
    'padding', 'margin', 'font-weight', 'font-size', 'text-align',
    'display', 'width', 'max-width', 'min-width',
    'border-left', 'border-right', 'border-top', 'border-bottom',
    'border-collapse', 'vertical-align', 'list-style-type',
    'overflow', 'white-space',
]

# Vertex AI 初期化フラグ
_vertex_initialized = False


def _init_vertex():
    """Vertex AI SDKを初期化する（1回のみ）"""
    global _vertex_initialized
    if _vertex_initialized:
        return
    import vertexai
    vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
    _vertex_initialized = True
    logger.info(f'Vertex AI初期化完了: project={VERTEX_PROJECT}, location={VERTEX_LOCATION}')


def strip_code_fences(text):
    """
    Geminiの出力から ```html...``` や ```...``` のコードフェンスを除去する
    """
    # ```html\n...\n``` パターン
    match = re.search(r'```(?:html)?\s*\n(.*?)\n\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 先頭の ```html と末尾の ``` を除去
    text = re.sub(r'^```(?:html)?\s*\n?', '', text.strip())
    text = re.sub(r'\n?```\s*$', '', text.strip())
    return text.strip()


def strip_style_blocks(text):
    """
    <style>...</style> ブロックを除去する
    """
    return re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)


def sanitize_html(html_content):
    """
    Geminiの出力HTMLをサニタイズする
    """
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def generate_answer(question_title, question_body, subject_name, body_format='text', media_paths=None, style='normal'):
    """
    Vertex AI (Gemini) を呼び出して回答を生成する（マルチモーダル対応）

    Args:
        question_title: 質問タイトル
        question_body: 質問本文
        subject_name: 教科名
        body_format: 質問の本文フォーマット
        media_paths: メディアファイルパスのリスト
        style: 'normal' または 'slide'

    Returns:
        HTML回答文字列

    Raises:
        Exception: API呼び出しに失敗した場合
    """
    from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
    from .prompts import get_prompt_for_subject, get_slide_prompt_for_subject

    _init_vertex()

    # スタイルに応じたプロンプトを取得
    if style == 'slide':
        system_prompt = get_slide_prompt_for_subject(subject_name)
    else:
        system_prompt = get_prompt_for_subject(subject_name)

    # ユーザプロンプトを構成
    user_prompt_text = f"""以下の質問にHTML形式で回答してください。

★重要: 必ずSVG図形、Chart.jsグラフ、またはMermaid.jsダイアグラムを最低1つ含めてください。テキストだけの回答は禁止です。
★重要: <!DOCTYPE html>や<html><head><body>タグは不要です。<style>と<script>と本文のHTMLだけを出力してください。

【教科】{subject_name}
【タイトル】{question_title}
【質問内容】
{question_body}
"""

    # マルチモーダルコンテンツを構成
    content_parts = []

    # メディアファイルを読み込み
    if media_paths:
        for media_info in media_paths:
            try:
                mime_type = media_info.get('mime', 'application/octet-stream')
                with open(media_info['path'], 'rb') as f:
                    data = f.read()
                content_parts.append(Part.from_data(data=data, mime_type=mime_type))
                logger.info(f'メディア読み込み成功: {media_info["path"]}')
            except Exception as e:
                logger.warning(f'メディア読み込み失敗: {media_info["path"]} - {e}')

    if media_paths:
        user_prompt_text += '\n添付されたメディアファイル（画像・音声・動画）も参考にして回答してください。'

    content_parts.append(user_prompt_text)

    logger.info(f'Vertex AI呼び出し開始: {question_title} ({subject_name}) メディア数={len(media_paths or [])}')

    try:
        model = GenerativeModel(
            model_name=VERTEX_MODEL_PRO,
            system_instruction=system_prompt,
        )

        response = model.generate_content(
            content_parts,
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=65536,
            ),
        )

        if response.text:
            # コードフェンス（```html...```）を除去
            html_answer = strip_code_fences(response.text)

            # HTMLタグが含まれていない場合は<p>タグで囲む
            if not any(tag in html_answer for tag in ['<p>', '<h', '<div>', '<ul>', '<ol>', '<svg>', '<style>']):
                html_answer = f'<div>{html_answer}</div>'

            logger.info(f'Vertex AI呼び出し成功: {question_title}')
            return html_answer
        else:
            raise ValueError('Vertex AIから空のレスポンスが返されました。')

    except Exception as e:
        logger.error(f'Vertex AI呼び出しエラー: {question_title} - {e}')
        raise


def _get_gemini_model(mode='flash'):
    """Geminiモデルのインスタンスを取得する（Vertex AI）
    
    Args:
        mode: 'pro' (高品質・初回回答) or 'flash' (高速・返信/注釈)
    """
    from vertexai.generative_models import GenerativeModel
    _init_vertex()
    model_name = VERTEX_MODEL_PRO if mode == 'pro' else VERTEX_MODEL_FLASH
    return GenerativeModel(model_name=model_name)


def generate_reply_text(question_title, question_body, answer_body,
                        thread_context, user_message, subject_name):
    """
    @aiメンション付き返信に対してAI返信テキストを生成する

    Returns:
        HTML形式の返信テキスト
    """
    from vertexai.generative_models import GenerationConfig

    model = _get_gemini_model()

    prompt = f"""あなたは高校生の学習を支援する教師AIです。
以下の質問・回答スレッドの文脈を踏まえて、ユーザの返信に対して丁寧にHTML形式で回答してください。
教科: {subject_name}

【元の質問】
タイトル: {question_title}
{question_body}

【回答内容】
{answer_body}

【返信スレッド】
{thread_context}

上記のスレッドに対して、ユーザのメッセージに丁寧に回答してください。

【出力ルール】
- 回答はHTML形式で出力してください。マークダウンのコードフェンス（```html...```）は使わないでください。
- 数式がある場合はKaTeX記法（$...$）を使ってください。
- 回答は日本語で行ってください。
- 返信なので簡潔に要点をまとめてください。
- <p>、<strong>、<em>、<ul>、<li>などのHTMLタグを使ってください。
- インラインstyle属性で色やボックスを使い、わかりやすくしてください。"""

    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=0.7,
            max_output_tokens=2048,
        ),
    )

    if response.text:
        return strip_code_fences(response.text)
    raise ValueError('AI返信で空のレスポンスが返されました。')


def generate_annotation(selected_text, context_before, context_after,
                        annotation_type, subject_name,
                        question_title='', question_body=''):
    """
    数式導出や単語説明のAI注釈を生成する

    Returns:
        HTML形式の説明テキスト
    """
    from vertexai.generative_models import GenerationConfig

    model = _get_gemini_model()

    if annotation_type == 'formula':
        task_desc = '以下の数式の導出過程を丁寧にステップごとに説明してください'
    else:
        task_desc = '以下の単語・表現の意味を詳しく説明してください'

    prompt = f"""あなたは高校生の学習を支援する教師AIです。
教科: {subject_name}

{task_desc}。

【元の質問】
タイトル: {question_title}
{question_body}

【選択部分を含む文章の全体】
{context_before}

【対象テキスト（ユーザが選択した部分）】
{selected_text}

以下のルールで回答してください:
- HTML形式で出力してください。マークダウンのコードフェンス（```html...```）は使わないでください。
- 数式がある場合はKaTeX記法（$...$）を使ってください
- ポップアップ表示用なので要約して簡潔にまとめてください（3〜5文程度）
- <p>、<strong>、<em>、<mark>タグとインラインstyle属性を使ってください
- 回答は日本語で行ってください"""

    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=0.5,
            max_output_tokens=1024,
        ),
    )

    if response.text:
        return strip_code_fences(response.text)
    raise ValueError('AI注釈で空のレスポンスが返されました。')


def generate_supplements(answer_body, subject_name):
    """
    回答本文の重要単語・数式を自動検出し、補足情報を生成する

    Returns:
        補足情報のリスト [{'text': '...', 'type': '...', 'explanation': '...'}, ...]
    """
    from vertexai.generative_models import GenerationConfig

    model = _get_gemini_model()

    prompt = f"""あなたは高校生の学習を支援するAIです。
教科: {subject_name}

以下の回答文から、高校生が理解に困る可能性のある重要な「専門用語」と「数式」を最大5つ検出し、
それぞれの簡潔な説明を生成してください。

【回答文】
{answer_body}

以下のJSON形式で出力してください（JSONのみ、他のテキストは不要）:
[
  {{"text": "検出した単語/数式", "type": "word or formula", "explanation": "Markdownで簡潔な説明"}}
]

該当するものがなければ空の配列 [] を返してください。"""

    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )

    if response.text:
        import json
        text = response.text.strip()
        # JSON部分を抽出
        if '```' in text:
            import re
            match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f'補完情報のJSON解析失敗: {text[:200]}')
            return []

    return []

