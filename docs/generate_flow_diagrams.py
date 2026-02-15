#!/usr/bin/env python3
"""
SIRISA 処理フロー図生成スクリプト

8つの主要機能について Graphviz で処理フローを作成し、PNG 画像を出力する。
出力先: docs/flows/*.png
"""

import graphviz
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'flows')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===== 共通スタイル =====
GRAPH_ATTR = {
    'rankdir': 'TB',
    'fontname': 'Noto Sans CJK JP',
    'fontsize': '11',
    'bgcolor': '#FAFBFC',
    'pad': '0.5',
    'nodesep': '0.4',
    'ranksep': '0.5',
    'dpi': '150',
}

NODE_STYLES = {
    'start':    {'shape': 'circle', 'style': 'filled', 'fillcolor': '#2ECC71', 'fontcolor': 'white', 'width': '0.5', 'fixedsize': 'true', 'fontsize': '10'},
    'end':      {'shape': 'doublecircle', 'style': 'filled', 'fillcolor': '#E74C3C', 'fontcolor': 'white', 'width': '0.5', 'fixedsize': 'true', 'fontsize': '10'},
    'action':   {'shape': 'box', 'style': 'rounded,filled', 'fillcolor': '#EBF5FB', 'color': '#2980B9', 'fontname': 'Noto Sans CJK JP', 'fontsize': '10'},
    'decision': {'shape': 'diamond', 'style': 'filled', 'fillcolor': '#FEF9E7', 'color': '#F39C12', 'fontname': 'Noto Sans CJK JP', 'fontsize': '9'},
    'async':    {'shape': 'box', 'style': 'filled,dashed', 'fillcolor': '#F5EEF8', 'color': '#8E44AD', 'fontname': 'Noto Sans CJK JP', 'fontsize': '10'},
    'frontend': {'shape': 'box', 'style': 'filled', 'fillcolor': '#FDEBD0', 'color': '#E67E22', 'fontname': 'Noto Sans CJK JP', 'fontsize': '10'},
    'db':       {'shape': 'cylinder', 'style': 'filled', 'fillcolor': '#E8F8F5', 'color': '#1ABC9C', 'fontname': 'Noto Sans CJK JP', 'fontsize': '10'},
    'api':      {'shape': 'parallelogram', 'style': 'filled', 'fillcolor': '#EBF5FB', 'color': '#3498DB', 'fontname': 'Noto Sans CJK JP', 'fontsize': '10'},
    'external': {'shape': 'box3d', 'style': 'filled', 'fillcolor': '#FADBD8', 'color': '#E74C3C', 'fontname': 'Noto Sans CJK JP', 'fontsize': '10'},
}

EDGE_ATTR = {
    'fontname': 'Noto Sans CJK JP',
    'fontsize': '9',
    'color': '#566573',
}


def new_graph(name, title):
    """新しい有向グラフを作成"""
    g = graphviz.Digraph(name, format='png')
    g.attr(**GRAPH_ATTR)
    g.attr(label=f'<<B>{title}</B>>', labelloc='t', fontsize='16')
    g.edge_attr.update(**EDGE_ATTR)
    return g


def add_node(g, name, label, style='action'):
    """ノードを追加"""
    g.node(name, label, **NODE_STYLES[style])


def save(g, filename):
    """グラフを保存"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    g.render(filepath, cleanup=True)
    print(f'  ✓ {filepath}.png')


# =====================================================================
# 1. 質問投稿機能
# =====================================================================
def create_question_flow():
    g = new_graph('question', '質問投稿 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'access', 'GET /questions/new/\n質問作成ページ表示', 'frontend')
    add_node(g, 'load_draft', '下書き (QuestionDraft)\n読み込み', 'db')
    add_node(g, 'has_draft', '下書きあり?', 'decision')
    add_node(g, 'prefill', 'フォームに\n下書き内容をセット', 'action')
    add_node(g, 'show_form', 'フォーム表示\n(タイトル/教科/本文/公開範囲)', 'frontend')
    add_node(g, 'submit', 'POST 送信', 'frontend')
    add_node(g, 'validate', 'QuestionForm\nバリデーション', 'action')
    add_node(g, 'valid', 'バリデーション\n成功?', 'decision')
    add_node(g, 'show_errors', 'エラー表示', 'frontend')
    add_node(g, 'check_group', 'visibility ==\n"group"?', 'decision')
    add_node(g, 'validate_group', 'StudyGroup存在確認\n+ メンバーシップ確認', 'action')
    add_node(g, 'save_question', 'Question レコード保存', 'db')
    add_node(g, 'save_media', 'QuestionMedia 保存\n(添付ファイル, ≤100MB)', 'db')
    add_node(g, 'delete_draft', 'QuestionDraft 削除', 'db')
    add_node(g, 'check_ai', 'AI使用回数\n≤100回/日?', 'decision')
    add_node(g, 'dispatch_ai', 'Celery Task\ngenerate_ai_answer.delay()', 'async')
    add_node(g, 'create_pending', 'Answer×2 作成\n(normal + slide)\nstatus=pending', 'db')
    add_node(g, 'call_gemini', 'Vertex AI\nGemini 2.5 Pro 呼び出し', 'external')
    add_node(g, 'save_answer', 'Answer.body 更新\nstatus=completed', 'db')
    add_node(g, 'redirect', 'リダイレクト\n質問詳細ページ', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'access')
    g.edge('access', 'load_draft')
    g.edge('load_draft', 'has_draft')
    g.edge('has_draft', 'prefill', label='Yes')
    g.edge('has_draft', 'show_form', label='No')
    g.edge('prefill', 'show_form')
    g.edge('show_form', 'submit')
    g.edge('submit', 'validate')
    g.edge('validate', 'valid')
    g.edge('valid', 'show_errors', label='No')
    g.edge('show_errors', 'show_form')
    g.edge('valid', 'check_group', label='Yes')
    g.edge('check_group', 'validate_group', label='Yes')
    g.edge('check_group', 'save_question', label='No (public)')
    g.edge('validate_group', 'save_question')
    g.edge('save_question', 'save_media')
    g.edge('save_media', 'delete_draft')
    g.edge('delete_draft', 'check_ai')
    g.edge('check_ai', 'dispatch_ai', label='Yes')
    g.edge('check_ai', 'redirect', label='No (制限超過)')
    g.edge('dispatch_ai', 'redirect', label='sync\n(即座にリダイレクト)')
    g.edge('redirect', 'end')

    # 非同期フロー（破線）
    g.edge('dispatch_ai', 'create_pending', style='dashed', color='#8E44AD', label='async')
    g.edge('create_pending', 'call_gemini', style='dashed', color='#8E44AD')
    g.edge('call_gemini', 'save_answer', style='dashed', color='#8E44AD')

    save(g, '01_question_posting')


# =====================================================================
# 2. 回答機能
# =====================================================================
def create_answer_flow():
    g = new_graph('answer', '回答投稿 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'access', 'GET /questions/<pk>/answer/\n回答作成ページ表示', 'frontend')
    add_node(g, 'load_draft', 'AnswerDraft\n読み込み', 'db')
    add_node(g, 'has_draft', '下書きあり?', 'decision')
    add_node(g, 'prefill', 'フォームに\n下書き内容をセット', 'action')
    add_node(g, 'show_form', 'フォーム表示\n(本文/形式選択)', 'frontend')
    add_node(g, 'submit', 'POST 送信', 'frontend')
    add_node(g, 'validate', 'AnswerForm\nバリデーション', 'action')
    add_node(g, 'valid', '成功?', 'decision')
    add_node(g, 'show_errors', 'エラー表示', 'frontend')
    add_node(g, 'save_answer', 'Answer レコード保存\n(question, user)', 'db')
    add_node(g, 'save_media', 'AnswerMedia 保存\n(添付ファイル, ≤100MB)', 'db')
    add_node(g, 'delete_draft', 'AnswerDraft 削除', 'db')
    add_node(g, 'redirect', 'リダイレクト\n質問詳細ページ', 'frontend')
    add_node(g, 'render', '回答表示\nbleach.clean() → HTML', 'action')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'access')
    g.edge('access', 'load_draft')
    g.edge('load_draft', 'has_draft')
    g.edge('has_draft', 'prefill', label='Yes')
    g.edge('has_draft', 'show_form', label='No')
    g.edge('prefill', 'show_form')
    g.edge('show_form', 'submit')
    g.edge('submit', 'validate')
    g.edge('validate', 'valid')
    g.edge('valid', 'show_errors', label='No')
    g.edge('show_errors', 'show_form')
    g.edge('valid', 'save_answer', label='Yes')
    g.edge('save_answer', 'save_media')
    g.edge('save_media', 'delete_draft')
    g.edge('delete_draft', 'redirect')
    g.edge('redirect', 'render')
    g.edge('render', 'end')

    save(g, '02_answer_posting')


# =====================================================================
# 3. 返信機能
# =====================================================================
def create_reply_flow():
    g = new_graph('reply', '返信 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'input', 'テキスト入力\n(返信フォーム)', 'frontend')
    add_node(g, 'submit', 'AJAX POST 送信\nX-Requested-With:\nXMLHttpRequest', 'frontend')
    add_node(g, 'validate', 'ReplyForm\nバリデーション', 'action')
    add_node(g, 'valid', '成功?', 'decision')
    add_node(g, 'error_json', 'JSONエラー応答', 'frontend')
    add_node(g, 'save_reply', 'Reply レコード保存', 'db')
    add_node(g, 'save_media', 'ReplyMedia 保存\n(添付ファイル)', 'db')
    add_node(g, 'check_ai', '@ai を含む?', 'decision')
    add_node(g, 'check_limit', 'AI使用回数\n≤100回/日?', 'decision')
    add_node(g, 'dispatch_ai', 'Celery Task\ngenerate_ai_reply.delay()', 'async')
    add_node(g, 'json_resp', 'JsonResponse\n(reply_html,\nai_reply_pending)', 'api')
    add_node(g, 'insert_dom', 'reply_html を\nDOM に挿入\n+ KaTeX レンダリング', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'input')
    g.edge('input', 'submit')
    g.edge('submit', 'validate')
    g.edge('validate', 'valid')
    g.edge('valid', 'error_json', label='No')
    g.edge('error_json', 'input')
    g.edge('valid', 'save_reply', label='Yes')
    g.edge('save_reply', 'save_media')
    g.edge('save_media', 'check_ai')
    g.edge('check_ai', 'check_limit', label='Yes')
    g.edge('check_ai', 'json_resp', label='No')
    g.edge('check_limit', 'dispatch_ai', label='Yes')
    g.edge('check_limit', 'json_resp', label='No (制限超過)')
    g.edge('dispatch_ai', 'json_resp')
    g.edge('json_resp', 'insert_dom')
    g.edge('insert_dom', 'end')

    save(g, '03_reply_posting')


# =====================================================================
# 4. AI返信機能
# =====================================================================
def create_ai_reply_flow():
    g = new_graph('ai_reply', 'AI返信 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'trigger', 'ユーザが\n"@ai" を含む\n返信を投稿', 'frontend')
    add_node(g, 'dispatch', 'Celery Task\ngenerate_ai_reply\n.delay(reply_pk)', 'async')
    add_node(g, 'create_pending', 'AI Reply レコード作成\nstatus=pending\n"AI返信を生成中..."', 'db')
    add_node(g, 'build_context', 'スレッド文脈構築\n(質問 + 回答 +\n直近10件の返信)', 'action')
    add_node(g, 'call_gemini', 'Vertex AI\nGemini 2.5 Flash\n呼び出し', 'external')
    add_node(g, 'save_reply', 'Reply.body 更新\nstatus=completed', 'db')
    add_node(g, 'poll_start', 'フロントエンド\npollNewAIReply()\n4秒間隔', 'frontend')
    add_node(g, 'check_pending', 'GET /api/answers/\n<pk>/replies/\n未表示AI返信検索', 'api')
    add_node(g, 'insert_pending', 'ペンディング\nカード表示', 'frontend')
    add_node(g, 'poll_status', 'GET /api/replies/\n<pk>/status/\n4秒間隔ポーリング', 'api')
    add_node(g, 'status_check', 'status ==\ncompleted?', 'decision')
    add_node(g, 'replace_html', 'ペンディングカード\n→ 完成HTML差替\n+ KaTeX レンダリング', 'frontend')
    add_node(g, 'failed', 'エラーメッセージ\n表示', 'frontend')
    add_node(g, 'end', '終了', 'end')

    # サーバ側フロー（非同期）
    g.edge('start', 'trigger')
    g.edge('trigger', 'dispatch')
    g.edge('dispatch', 'create_pending', style='dashed', color='#8E44AD', label='async')
    g.edge('create_pending', 'build_context', style='dashed', color='#8E44AD')
    g.edge('build_context', 'call_gemini', style='dashed', color='#8E44AD')
    g.edge('call_gemini', 'save_reply', style='dashed', color='#8E44AD')

    # フロントエンド側フロー（ポーリング）
    g.edge('trigger', 'poll_start', label='ai_reply_pending\n= true')
    g.edge('poll_start', 'check_pending')
    g.edge('check_pending', 'insert_pending')
    g.edge('insert_pending', 'poll_status')
    g.edge('poll_status', 'status_check')
    g.edge('status_check', 'poll_status', label='pending\n(4秒後再試行)')
    g.edge('status_check', 'replace_html', label='completed')
    g.edge('status_check', 'failed', label='failed')
    g.edge('replace_html', 'end')
    g.edge('failed', 'end')

    save(g, '04_ai_reply')


# =====================================================================
# 5. 数式の導出過程表示機能
# =====================================================================
def create_formula_flow():
    g = new_graph('formula', '数式の導出過程表示 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'click', 'KaTeX 数式を\nクリック', 'frontend')
    add_node(g, 'detect', 'クリック検出\n(.katex 要素)\ne.stopPropagation()', 'frontend')
    add_node(g, 'context', 'コンテキスト判定\n(Shadow DOM or\n通常DOM or 返信)', 'action')
    add_node(g, 'extract', 'formulaText 抽出\nkatexEl.textContent', 'action')
    add_node(g, 'show_loading', 'ローディング\nポップアップ表示\n"数式の導出を生成中..."', 'frontend')
    add_node(g, 'api_call', 'POST /api/annotations/\n{answer_id, selected_text,\ntype: "formula",\ncontext_before}', 'api')
    add_node(g, 'check_cache', '既存アノテーション\n検索 (同一回答+\n同一テキスト+type)', 'db')
    add_node(g, 'has_cache', 'キャッシュ\nあり?', 'decision')
    add_node(g, 'return_cache', 'キャッシュ済み\nexplanation 返却', 'api')
    add_node(g, 'check_limit', 'AIUsageLog\n≤100回/日?', 'decision')
    add_node(g, 'limit_error', '制限超過\nエラー応答', 'api')
    add_node(g, 'call_gemini', 'Vertex AI\nGemini 2.5 Flash\ngenerate_annotation()\ntype=formula', 'external')
    add_node(g, 'save_annotation', 'AIAnnotation\nレコード保存', 'db')
    add_node(g, 'return_explain', 'explanation\nHTML 返却', 'api')
    add_node(g, 'show_popup', 'ポップアップ表示\n#annotationPopup\n+ KaTeX再レンダリング\n+ 位置調整', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'click')
    g.edge('click', 'detect')
    g.edge('detect', 'context')
    g.edge('context', 'extract')
    g.edge('extract', 'show_loading')
    g.edge('show_loading', 'api_call')
    g.edge('api_call', 'check_cache')
    g.edge('check_cache', 'has_cache')
    g.edge('has_cache', 'return_cache', label='Yes')
    g.edge('has_cache', 'check_limit', label='No')
    g.edge('check_limit', 'limit_error', label='No')
    g.edge('check_limit', 'call_gemini', label='Yes')
    g.edge('call_gemini', 'save_annotation')
    g.edge('save_annotation', 'return_explain')
    g.edge('return_cache', 'show_popup')
    g.edge('return_explain', 'show_popup')
    g.edge('limit_error', 'show_popup', label='エラー表示')
    g.edge('show_popup', 'end')

    save(g, '05_formula_derivation')


# =====================================================================
# 6. 単語の意味説明機能
# =====================================================================
def create_word_annotation_flow():
    g = new_graph('word', '単語の意味説明 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'select', 'テキストを\nマウスで選択\n(2〜500文字)', 'frontend')
    add_node(g, 'detect_area', '選択領域検出\n(Shadow DOM /\n通常DOM /\n返信エリア)', 'action')
    add_node(g, 'show_btn', '"AIに説明を聞く"\nボタン表示\n(選択範囲の近く)', 'frontend')
    add_node(g, 'click_btn', 'ボタンクリック\nor 右クリック\nメニュー選択', 'frontend')
    add_node(g, 'show_loading', 'ローディング\nポップアップ表示', 'frontend')
    add_node(g, 'api_call', 'POST /api/annotations/\n{answer_id, selected_text,\ntype: "word",\ncontext_before}', 'api')
    add_node(g, 'check_cache', '既存アノテーション\n検索', 'db')
    add_node(g, 'has_cache', 'キャッシュ?', 'decision')
    add_node(g, 'return_cache', 'キャッシュ済み\nexplanation 返却', 'api')
    add_node(g, 'check_limit', 'AI使用回数\nチェック', 'decision')
    add_node(g, 'call_gemini', 'Vertex AI\nGemini 2.5 Flash\ngenerate_annotation()\ntype=word', 'external')
    add_node(g, 'save_annotation', 'AIAnnotation\nレコード保存', 'db')
    add_node(g, 'return_explain', 'explanation 返却', 'api')
    add_node(g, 'highlight', 'highlightSelection()\n全出現箇所を\n紫色ハイライト\n(SVG内は除外)', 'frontend')
    add_node(g, 'show_popup', 'ポップアップ表示\n+ ホバー時持続表示', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'select')
    g.edge('select', 'detect_area')
    g.edge('detect_area', 'show_btn')
    g.edge('show_btn', 'click_btn')
    g.edge('click_btn', 'show_loading')
    g.edge('show_loading', 'api_call')
    g.edge('api_call', 'check_cache')
    g.edge('check_cache', 'has_cache')
    g.edge('has_cache', 'return_cache', label='Yes')
    g.edge('has_cache', 'check_limit', label='No')
    g.edge('check_limit', 'call_gemini', label='Yes')
    g.edge('check_limit', 'show_popup', label='No\n(制限超過エラー)')
    g.edge('call_gemini', 'save_annotation')
    g.edge('save_annotation', 'return_explain')
    g.edge('return_cache', 'highlight')
    g.edge('return_explain', 'highlight')
    g.edge('highlight', 'show_popup')
    g.edge('show_popup', 'end')

    save(g, '06_word_annotation')


# =====================================================================
# 7. 小グループ機能
# =====================================================================
def create_group_flow():
    g = new_graph('group', '小グループ 処理フロー')

    # --- グループ作成 ---
    with g.subgraph(name='cluster_create') as c:
        c.attr(label='<<B>グループ作成</B>>', style='rounded,filled', color='#2980B9', fillcolor='#EBF5FB')
        add_node(c, 'gc_start', '開始', 'start')
        add_node(c, 'gc_form', 'GET /groups/new/\nグループ名+説明\n入力フォーム', 'frontend')
        add_node(c, 'gc_validate', 'StudyGroupForm\nバリデーション', 'action')
        add_node(c, 'gc_save', 'StudyGroup 保存\n(invite_code 自動生成\nUUID 8文字)', 'db')
        add_node(c, 'gc_member', 'GroupMembership\n作成 (role=owner)', 'db')
        add_node(c, 'gc_redirect', 'リダイレクト\nグループ詳細', 'frontend')

        c.edge('gc_start', 'gc_form')
        c.edge('gc_form', 'gc_validate')
        c.edge('gc_validate', 'gc_save')
        c.edge('gc_save', 'gc_member')
        c.edge('gc_member', 'gc_redirect')

    # --- 招待コードで参加 ---
    with g.subgraph(name='cluster_join') as c:
        c.attr(label='<<B>招待コードで参加</B>>', style='rounded,filled', color='#27AE60', fillcolor='#E8F8F5')
        add_node(c, 'gj_start', '開始', 'start')
        add_node(c, 'gj_form', 'POST /groups/join/\n招待コード入力', 'frontend')
        add_node(c, 'gj_validate', 'コード検証\n(大文字変換\n+ 存在確認)', 'action')
        add_node(c, 'gj_found', 'グループ\n見つかった?', 'decision')
        add_node(c, 'gj_error', 'エラー表示\n"無効な招待コード"', 'frontend')
        add_node(c, 'gj_join', 'GroupMembership\nget_or_create\n(role=member)', 'db')
        add_node(c, 'gj_redirect', 'リダイレクト\nグループ詳細', 'frontend')

        c.edge('gj_start', 'gj_form')
        c.edge('gj_form', 'gj_validate')
        c.edge('gj_validate', 'gj_found')
        c.edge('gj_found', 'gj_error', label='No')
        c.edge('gj_error', 'gj_form')
        c.edge('gj_found', 'gj_join', label='Yes')
        c.edge('gj_join', 'gj_redirect')

    # --- メンバー管理 ---
    with g.subgraph(name='cluster_manage') as c:
        c.attr(label='<<B>メンバー管理 (オーナーのみ)</B>>', style='rounded,filled', color='#E67E22', fillcolor='#FDEBD0')
        add_node(c, 'gm_detail', 'GET /groups/<pk>/\nメンバー一覧\n+ グループ質問一覧', 'frontend')
        add_node(c, 'gm_remove', 'POST /<pk>/remove/<uid>/\nメンバー除外', 'action')
        add_node(c, 'gm_regen', 'POST /<pk>/regenerate-code/\n招待コード再生成', 'action')
        add_node(c, 'gm_delete', 'POST /<pk>/delete/\nグループ削除\n(is_active=False)', 'action')
        add_node(c, 'gm_leave', 'POST /<pk>/leave/\n脱退', 'action')
        add_node(c, 'gm_is_owner', 'オーナーが\n最後の1人?', 'decision')
        add_node(c, 'gm_deactivate', 'グループ\n無効化', 'db')
        add_node(c, 'gm_del_member', 'Membership\n削除', 'db')

        c.edge('gm_detail', 'gm_remove')
        c.edge('gm_detail', 'gm_regen')
        c.edge('gm_detail', 'gm_delete')
        c.edge('gm_detail', 'gm_leave')
        c.edge('gm_leave', 'gm_is_owner')
        c.edge('gm_is_owner', 'gm_deactivate', label='Yes')
        c.edge('gm_is_owner', 'gm_del_member', label='No')

    save(g, '07_study_groups')


# =====================================================================
# 8. ログイン機能
# =====================================================================
def create_login_flow():
    g = new_graph('login', 'ログイン (Firebase Authentication) 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'login_page', 'GET /accounts/login/\nログインページ表示', 'frontend')
    add_node(g, 'choose', 'ログイン方法\n選択', 'decision')

    # --- Google Sign-In ---
    add_node(g, 'google_click', '"Googleでサインイン"\nボタンクリック', 'frontend')
    add_node(g, 'google_redirect', 'Firebase SDK\nsignInWithRedirect()\nGoogle OAuth画面へ', 'external')
    add_node(g, 'google_consent', 'Google\nアカウント選択\n+ 同意', 'frontend')
    add_node(g, 'google_return', 'リダイレクト戻り\ngetRedirectResult()', 'frontend')

    # --- Email Link ---
    add_node(g, 'email_input', 'メールアドレス入力\n"メールリンクを送信"\nクリック', 'frontend')
    add_node(g, 'send_link', 'Firebase SDK\nsendSignInLinkToEmail()\nemail → localStorage', 'external')
    add_node(g, 'email_sent', '"メール送信完了"\n表示', 'frontend')
    add_node(g, 'click_link', 'メール内リンク\nクリック', 'frontend')
    add_node(g, 'email_callback', 'GET /accounts/firebase/\nemail-link/\nsignInWithEmailLink()', 'frontend')

    # --- 共通フロー ---
    add_node(g, 'get_token', 'user.getIdToken()\nFirebase IDトークン取得', 'action')
    add_node(g, 'post_token', 'POST /accounts/\nfirebase/callback/\n{idToken}', 'api')
    add_node(g, 'verify_token', 'Firebase Admin SDK\nverify_id_token()\nuid/email/name 抽出', 'external')
    add_node(g, 'clear_deleted', '論理削除済みユーザの\nfirebase_uid クリア', 'db')
    add_node(g, 'find_user', 'User 検索\n(firebase_uid\n→ email fallback)', 'db')
    add_node(g, 'user_exists', 'ユーザ\n存在する?', 'decision')

    # --- 既存ユーザ ---
    add_node(g, 'django_login', 'Django login()\nセッション作成\n(30日間有効)', 'action')
    add_node(g, 'redirect_home', 'リダイレクト\nホームページ /', 'frontend')

    # --- 新規ユーザ ---
    add_node(g, 'store_session', 'セッションに\nfirebase_uid/email\n保存', 'action')
    add_node(g, 'redirect_register', 'リダイレクト\n/accounts/register/', 'frontend')
    add_node(g, 'register_form', 'ユーザ名入力\n(メールアドレスは\n自動入力)', 'frontend')
    add_node(g, 'register_validate', 'RegisterForm\nバリデーション\n(ユーザ名重複確認)', 'action')
    add_node(g, 'create_user', 'User 作成\nfirebase_uid 紐付け\nis_verified=True\nset_unusable_password()', 'db')
    add_node(g, 'register_login', 'Django login()\nセッション作成', 'action')

    add_node(g, 'end', '終了', 'end')

    # メインフロー
    g.edge('start', 'login_page')
    g.edge('login_page', 'choose')

    # Google フロー
    g.edge('choose', 'google_click', label='Google')
    g.edge('google_click', 'google_redirect')
    g.edge('google_redirect', 'google_consent')
    g.edge('google_consent', 'google_return')
    g.edge('google_return', 'get_token')

    # Email フロー
    g.edge('choose', 'email_input', label='メールリンク')
    g.edge('email_input', 'send_link')
    g.edge('send_link', 'email_sent')
    g.edge('email_sent', 'click_link')
    g.edge('click_link', 'email_callback')
    g.edge('email_callback', 'get_token')

    # 共通フロー
    g.edge('get_token', 'post_token')
    g.edge('post_token', 'verify_token')
    g.edge('verify_token', 'clear_deleted')
    g.edge('clear_deleted', 'find_user')
    g.edge('find_user', 'user_exists')

    # 既存ユーザ
    g.edge('user_exists', 'django_login', label='Yes')
    g.edge('django_login', 'redirect_home')
    g.edge('redirect_home', 'end')

    # 新規ユーザ
    g.edge('user_exists', 'store_session', label='No')
    g.edge('store_session', 'redirect_register')
    g.edge('redirect_register', 'register_form')
    g.edge('register_form', 'register_validate')
    g.edge('register_validate', 'create_user')
    g.edge('create_user', 'register_login')
    g.edge('register_login', 'redirect_home')

    save(g, '08_login_firebase')


# =====================================================================
# メイン
# =====================================================================
def main():
    print('SIRISA 処理フロー図を生成中...\n')

    create_question_flow()
    create_answer_flow()
    create_reply_flow()
    create_ai_reply_flow()
    create_formula_flow()
    create_word_annotation_flow()
    create_group_flow()
    create_login_flow()

    print(f'\n全{8}枚の処理フロー図を {OUTPUT_DIR}/ に出力しました。')


if __name__ == '__main__':
    main()
