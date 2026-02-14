"""
SIRISA エクスポート機能
質問と回答をCSV, XLSX, PDF, Markdown, TXT形式で出力
"""
import csv
import io
import re
from html.parser import HTMLParser
from django.http import HttpResponse
from openpyxl import Workbook
from weasyprint import HTML as WeasyHTML

from .utils import render_body


class _HTMLTextExtractor(HTMLParser):
    """HTMLからテキストを抽出するパーサ"""
    def __init__(self):
        super().__init__()
        self.result = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._skip = True
        elif tag == 'br':
            self.result.append('\n')
        elif tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'):
            self.result.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._skip = False
        elif tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.result.append('\n')

    def handle_data(self, data):
        if not self._skip:
            self.result.append(data)

    def get_text(self):
        text = ''.join(self.result)
        # 連続する空行を1つに
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


def html_to_text(html_str):
    """HTMLからテキストを抽出する"""
    if not html_str:
        return ''
    # display:noneのスライドも含めるため、style属性のdisplay:noneを除去
    html_str = re.sub(r'display\s*:\s*none\s*;?', '', html_str, flags=re.IGNORECASE)
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html_str)
        return parser.get_text()
    except Exception:
        # パース失敗時はタグを単純除去
        return re.sub(r'<[^>]+>', '', html_str)


def export_csv(question, answers):
    """CSV形式でエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="question_{question.pk}.csv"'

    writer = csv.writer(response)
    writer.writerow(['種別', '投稿者', '教科', 'タイトル', '本文', '投稿日時'])

    # 質問行
    writer.writerow([
        '質問', question.user.username, question.display_subject,
        question.title, question.body, question.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    ])

    # 回答行
    for answer in answers:
        writer.writerow([
            'AI回答' if answer.is_ai_generated else '回答',
            answer.user.username, '', '',
            answer.body, answer.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


def export_xlsx(question, answers):
    """XLSX形式でエクスポート"""
    wb = Workbook()

    # 質問シート
    ws_q = wb.active
    ws_q.title = '質問'
    headers_q = ['タイトル', '教科', '投稿者', '本文', '投稿日時', '状態']
    ws_q.append(headers_q)
    ws_q.append([
        question.title, question.display_subject, question.user.username,
        question.body, question.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        '解決済み' if question.is_resolved else '未解決',
    ])

    # 回答シート
    ws_a = wb.create_sheet('回答')
    headers_a = ['回答者', '種別', '本文', '投稿日時']
    ws_a.append(headers_a)
    for answer in answers:
        ws_a.append([
            answer.user.username,
            'AI回答' if answer.is_ai_generated else '人間の回答',
            answer.body,
            answer.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="question_{question.pk}.xlsx"'
    wb.save(response)
    return response


def export_pdf(question, answers):
    """PDF形式でエクスポート"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head><meta charset="utf-8"><title>{question.title}</title>
    <style>
        body {{ font-family: 'Noto Sans CJK JP', 'Noto Sans JP', sans-serif; margin: 40px; font-size: 14px; }}
        h1 {{ color: #2c3e50; font-size: 20px; border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
        h2 {{ color: #34495e; font-size: 16px; margin-top: 24px; }}
        .meta {{ color: #7f8c8d; font-size: 12px; margin-bottom: 16px; }}
        .answer {{ border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin: 12px 0; }}
        .ai-answer {{ background: #f0f9ff; border-color: #3498db; }}
        .badge {{ background: #3498db; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
    </style></head>
    <body>
        <h1>{question.title}</h1>
        <div class="meta">
            教科: {question.display_subject} | 投稿者: {question.user.username} |
            日時: {question.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        <div>{render_body(question.body, question.body_format)}</div>
        <h2>回答 ({len(answers)}件)</h2>
    """

    for answer in answers:
        ai_class = ' ai-answer' if answer.is_ai_generated else ''
        ai_badge = ' <span class="badge">AI回答</span>' if answer.is_ai_generated else ''
        # AI回答の場合: display:noneのスライドもすべて表示し、scriptタグを除去
        answer_html = render_body(answer.body, answer.body_format)
        if answer.is_ai_generated:
            answer_html = re.sub(r'display\s*:\s*none\s*;?', '', answer_html, flags=re.IGNORECASE)
            answer_html = re.sub(r'<script[^>]*>.*?</script>', '', answer_html, flags=re.DOTALL | re.IGNORECASE)
        html_content += f"""
        <div class="answer{ai_class}">
            <div class="meta">{answer.user.username}{ai_badge} | {answer.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>{answer_html}</div>
        </div>
        """

    html_content += '</body></html>'

    pdf = WeasyHTML(string=html_content).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="question_{question.pk}.pdf"'
    return response


def export_markdown(question, answers):
    """Markdown形式でエクスポート"""
    content = f"""# {question.title}

**教科**: {question.display_subject}
**投稿者**: {question.user.username}
**日時**: {question.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**状態**: {'解決済み' if question.is_resolved else '未解決'}

---

## 質問内容

{question.body}

---

## 回答 ({len(answers)}件)

"""
    for i, answer in enumerate(answers, 1):
        ai_mark = ' [AI回答]' if answer.is_ai_generated else ''
        # AI回答はHTMLなのでテキスト抽出（スライドの全ページ含む）
        body_text = html_to_text(answer.body) if answer.is_ai_generated else answer.body
        content += f"""### 回答 {i}{ai_mark}

**回答者**: {answer.user.username}
**日時**: {answer.created_at.strftime('%Y-%m-%d %H:%M:%S')}

{body_text}

---

"""

    response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="question_{question.pk}.md"'
    return response


def export_txt(question, answers):
    """TXT形式でエクスポート"""
    content = f"""{'=' * 60}
質問: {question.title}
{'=' * 60}
教科: {question.display_subject}
投稿者: {question.user.username}
日時: {question.created_at.strftime('%Y-%m-%d %H:%M:%S')}
状態: {'解決済み' if question.is_resolved else '未解決'}
{'=' * 60}

【質問内容】
{question.body}

{'=' * 60}
回答 ({len(answers)}件)
{'=' * 60}
"""
    for i, answer in enumerate(answers, 1):
        ai_mark = ' [AI回答]' if answer.is_ai_generated else ''
        content += f"""
{'-' * 40}
回答 {i}{ai_mark}
回答者: {answer.user.username}
日時: {answer.created_at.strftime('%Y-%m-%d %H:%M:%S')}
{'-' * 40}
{answer.body}
"""

    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="question_{question.pk}.txt"'
    return response
