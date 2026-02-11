"""
SIRISA Gemini APIサービス
質問に対するAI回答を生成する
"""
import re
import logging
import bleach
from django.conf import settings

logger = logging.getLogger('gemini')

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


def generate_answer(question_title, question_body, subject_name, body_format='text'):
    """
    Gemini APIを呼び出して回答を生成する

    Args:
        question_title: 質問タイトル
        question_body: 質問本文
        subject_name: 教科名
        body_format: 質問の本文フォーマット

    Returns:
        サニタイズ済みのHTML回答文字列

    Raises:
        Exception: API呼び出しに失敗した場合
    """
    import google.generativeai as genai
    from .prompts import get_prompt_for_subject

    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key == 'your-gemini-api-key-here':
        raise ValueError('Gemini APIキーが設定されていません。')

    genai.configure(api_key=api_key)

    # 教科別プロンプトを取得
    system_prompt = get_prompt_for_subject(subject_name)

    # ユーザプロンプトを構成
    user_prompt = f"""以下の質問にHTML形式で回答してください。

【教科】{subject_name}
【タイトル】{question_title}
【質問内容】
{question_body}
"""

    logger.info(f'Gemini API呼び出し開始: {question_title} ({subject_name})')

    try:
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            system_instruction=system_prompt,
        )

        response = model.generate_content(
            user_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
            ),
            request_options={'timeout': 60},
        )

        if response.text:
            # コードフェンス（```html...```）を除去
            html_answer = strip_code_fences(response.text)

            # HTMLタグが含まれていない場合は<p>タグで囲む
            if not any(tag in html_answer for tag in ['<p>', '<h', '<div>', '<ul>', '<ol>']):
                html_answer = f'<div>{html_answer}</div>'

            # サニタイズして返す
            sanitized = sanitize_html(html_answer)
            logger.info(f'Gemini API呼び出し成功: {question_title}')
            return sanitized
        else:
            raise ValueError('Gemini APIから空のレスポンスが返されました。')

    except Exception as e:
        logger.error(f'Gemini API呼び出しエラー: {question_title} - {e}')
        raise
