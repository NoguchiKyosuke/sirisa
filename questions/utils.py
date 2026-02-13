"""
SIRISA 共通ユーティリティ（テキスト変換等）
"""
import html as html_module
import re
from html.parser import HTMLParser
import markdown as md
import bleach

# HTML許可タグ
ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'ul', 'ol', 'li', 'hr', 'br', 'blockquote', 'strong', 'em',
    'div', 'span', 'sup', 'sub', 'dl', 'dt', 'dd',
    'mark', 'small', 'abbr', 'details', 'summary',
    'figure', 'figcaption', 'caption', 'colgroup', 'col',
    'b', 'i',
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
    'th': ['colspan', 'rowspan', 'scope'],
    'td': ['colspan', 'rowspan'],
    'col': ['span'],
    'abbr': ['title'],
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


# ===== AI回答HTML処理 =====

# 閉じタグ不要な（void / self-closing）要素
VOID_ELEMENTS = frozenset([
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
])


class _TagTracker(HTMLParser):
    """開いたタグを追跡して未閉じタグを検出するパーサ"""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.open_tags = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in VOID_ELEMENTS:
            self.open_tags.append(tag.lower())

    def handle_endtag(self, tag):
        tag = tag.lower()
        # 対応する最も近い開きタグを閉じる
        for i in range(len(self.open_tags) - 1, -1, -1):
            if self.open_tags[i] == tag:
                self.open_tags.pop(i)
                break


def close_unclosed_tags(html_str):
    """未閉じHTMLタグを閉じる"""
    tracker = _TagTracker()
    try:
        tracker.feed(html_str)
    except Exception:
        pass
    # 逆順で閉じタグを追加（内側から外側へ）
    closing = ''.join(f'</{tag}>' for tag in reversed(tracker.open_tags))
    return html_str + closing


def scope_style_tags(html_str, scope_class):
    """<style>タグの中身をスコープクラスで囲んで他の要素に影響を与えないようにする"""
    def replace_style(match):
        css = match.group(1)
        # CSSルールの先頭にスコープセレクタを追加
        scoped_css = re.sub(
            r'([^\s@{}/][^{]*?)\{',
            lambda m: f'.{scope_class} {m.group(0)}',
            css,
        )
        return f'<style>{scoped_css}</style>'
    return re.sub(r'<style[^>]*>(.*?)</style>', replace_style, html_str,
                  flags=re.DOTALL | re.IGNORECASE)


def sanitize_ai_html(html_str, answer_id):
    """AI回答HTMLをページ内表示用に安全にする（タグ閉じ+スタイルスコープ）
    
    - <style>: スコープクラスを付与し、回答内のみに影響するようにする
    - <script>: そのまま維持（除去しない）
    - 未閉じタグ: 自動で閉じタグを追加
    """
    scope_class = f'ai-answer-{answer_id}'
    # <style>をスコープ（除去ではなくスコープ化のみ）
    result = scope_style_tags(html_str, scope_class)
    # 未閉じタグを閉じる
    result = close_unclosed_tags(result)
    return result, scope_class
