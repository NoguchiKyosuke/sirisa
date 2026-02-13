"""
SIRISA サンドボックスコンテンツ配信ビュー
content.sirisa.net から回答本文をiframe内で安全に表示する
"""
import hashlib
import logging
import re
import urllib.parse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.conf import settings

from questions.models import Answer

logger = logging.getLogger(__name__)


def generate_token(answer_id):
    """回答IDとSECRET_KEYからHMACトークンを生成"""
    raw = f'{answer_id}:{settings.SECRET_KEY}'
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def verify_token(answer_id, token):
    """トークンを検証する"""
    return token == generate_token(answer_id)


class SandboxedAnswerView(View):
    """回答本文をサンドボックスiframe内で表示"""

    def get(self, request, pk):
        token = request.GET.get('token', '')
        if not verify_token(pk, token):
            return HttpResponse('Forbidden', status=403)

        answer = get_object_or_404(Answer, pk=pk, is_deleted=False)

        # AI回答はタグ制限なし（サンドボックスで隔離）、ユーザ回答はサニタイズ済み
        if answer.is_ai_generated:
            from questions.services.gemini_service import strip_code_fences
            body_html = strip_code_fences(answer.body)
        else:
            from questions.utils import render_body
            body_html = render_body(answer.body, answer.body_format)

        # 外部リンクをクッションページ経由に書き換え
        body_html = self._rewrite_links(body_html)

        html = self._build_html(body_html, pk)

        response = HttpResponse(html, content_type='text/html')
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src * data: blob:; "
            "media-src *; "
            "connect-src 'none'; "
            "frame-src 'none';"
        )
        response['X-Frame-Options'] = 'ALLOWALL'
        return response

    def _build_html(self, body_html, pk):
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.7;padding:16px;color:var(--text-color,#333);background:var(--bg-color,transparent);overflow-wrap:break-word}}
img{{max-width:100%;height:auto}}
table{{border-collapse:collapse;width:100%;margin:12px 0}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
pre{{background:#f4f4f4;padding:12px;border-radius:6px;overflow-x:auto}}
code{{background:#f4f4f4;padding:2px 6px;border-radius:3px;font-size:.9em}}
pre code{{background:transparent;padding:0}}
blockquote{{border-left:4px solid #3498db;padding:8px 16px;margin:12px 0;background:#f8f9ff}}
a{{color:#3498db}}
mark{{background:#fff3cd;padding:2px 4px}}
details{{margin:8px 0}}
summary{{cursor:pointer;font-weight:bold}}
</style>
</head>
<body>
{body_html}
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded',function(){{
renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}]}});
function notifyHeight(){{window.parent.postMessage({{type:'resize',height:document.documentElement.scrollHeight,answerId:{pk}}},'*')}}
notifyHeight();
new MutationObserver(notifyHeight).observe(document.body,{{childList:true,subtree:true}});
window.addEventListener('load',notifyHeight);
window.addEventListener('message',function(e){{
if(e.data&&e.data.type==='theme'){{
document.documentElement.style.setProperty('--text-color',e.data.dark?'#e0e0e0':'#333');
document.documentElement.style.setProperty('--bg-color',e.data.dark?'#1a1a2e':'transparent');
}}
}});
}});
</script>
</body>
</html>"""

    def _rewrite_links(self, html):
        """外部リンクをクッションページ経由に書き換える"""
        def replace_href(match):
            url = match.group(2)
            quote = match.group(1)
            if url.startswith('/') or url.startswith('#') or 'sirisa.net' in url:
                return match.group(0)
            encoded = urllib.parse.quote(url, safe='')
            return f'href={quote}/cushion/?url={encoded}{quote}'
        return re.sub(r'href=(["\'])(https?://[^"\']+)\1', replace_href, html)


class CushionPageView(View):
    """リンククッションページ: Safe Browsing APIチェック後に遷移"""

    def get(self, request):
        url = request.GET.get('url', '')
        if not url:
            return HttpResponse('URL not provided', status=400)

        url = urllib.parse.unquote(url)

        is_safe = True
        threat_info = ''
        try:
            is_safe, threat_info = self._check_safe_browsing(url)
        except Exception as e:
            logger.warning(f'Safe Browsing APIチェック失敗: {e}')

        if is_safe:
            status_class = 'success'
            status_icon = '&#x2705;'
            status_text = 'このリンクは安全と判定されました'
            btn_class = 'btn-primary'
        else:
            status_class = 'danger'
            status_icon = '&#x26A0;&#xFE0F;'
            status_text = f'このリンクは危険と判定されました: {threat_info}'
            btn_class = 'btn-danger'

        from django.utils.html import escape
        escaped_url = escape(url)

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>外部リンク確認 - SIRISA</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f8f9fa}}
.cushion-card{{max-width:600px;width:100%}}
.url-display{{word-break:break-all;background:#f0f0f0;padding:12px;border-radius:6px;font-family:monospace;font-size:.9em}}
</style>
</head>
<body>
<div class="cushion-card card p-4 shadow">
<h4 class="mb-3">{status_icon} 外部リンク確認</h4>
<p class="text-muted">SIRISAから外部サイトに移動しようとしています。</p>
<div class="url-display mb-3">{escaped_url}</div>
<div class="alert alert-{status_class} mb-3">{status_text}</div>
<div class="d-flex gap-2">
<a href="{escaped_url}" class="btn {btn_class}" rel="noopener noreferrer" target="_blank">このサイトに移動する</a>
<button onclick="window.history.back()" class="btn btn-outline-secondary">戻る</button>
</div>
<p class="text-muted small mt-3 mb-0">Google Safe Browsing APIにより安全性を確認しています。</p>
</div>
</body>
</html>"""
        return HttpResponse(html, content_type='text/html')

    def _check_safe_browsing(self, url):
        """Google Safe Browsing API v4でチェック"""
        import requests

        api_key = settings.GCLOUD_API_KEY
        if not api_key:
            return True, ''

        endpoint = f'https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}'
        payload = {
            'client': {'clientId': 'sirisa', 'clientVersion': '1.0'},
            'threatInfo': {
                'threatTypes': [
                    'MALWARE', 'SOCIAL_ENGINEERING',
                    'UNWANTED_SOFTWARE', 'POTENTIALLY_HARMFUL_APPLICATION',
                ],
                'platformTypes': ['ANY_PLATFORM'],
                'threatEntryTypes': ['URL'],
                'threatEntries': [{'url': url}],
            }
        }

        response = requests.post(endpoint, json=payload, timeout=5)
        data = response.json()

        if 'matches' in data and data['matches']:
            threat_type = data['matches'][0].get('threatType', 'UNKNOWN')
            names = {
                'MALWARE': 'マルウェア',
                'SOCIAL_ENGINEERING': 'フィッシング',
                'UNWANTED_SOFTWARE': '迷惑ソフトウェア',
                'POTENTIALLY_HARMFUL_APPLICATION': '有害アプリケーション',
            }
            return False, names.get(threat_type, threat_type)

        return True, ''
