"""
SIRISA 共通ユーティリティ（テキスト変換等）
"""
import html as html_module
import markdown as md
import bleach

# HTML許可タグ
ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'ul', 'ol', 'li', 'hr', 'br', 'blockquote', 'strong', 'em',
    'div', 'span', 'sup', 'sub', 'dl', 'dt', 'dd',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title'],
    'th': ['colspan', 'rowspan'],
    'td': ['colspan', 'rowspan'],
}

ALLOWED_ATTRIBUTES_HTML = {
    '*': ['class', 'style'],
    'a': ['href', 'title'],
    'th': ['colspan', 'rowspan'],
    'td': ['colspan', 'rowspan'],
}


def render_body(body, body_format):
    """本文をフォーマットに応じてHTML変換する"""
    if body_format == 'markdown':
        html = md.markdown(
            body,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code'],
        )
        return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    elif body_format == 'html':
        return bleach.clean(body, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES_HTML)
    else:
        # テキスト形式: 改行を<br>に変換
        escaped = html_module.escape(body)
        return escaped.replace('\n', '<br>')
