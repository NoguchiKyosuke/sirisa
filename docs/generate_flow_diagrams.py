#!/usr/bin/env python3
"""
SIRISA 処理フロー図生成スクリプト

22の機能 + システムアーキテクチャについて Graphviz で処理フローを作成し、PNG 画像を出力する。
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
    add_node(g, 'access', '質問作成ページ表示', 'frontend')
    add_node(g, 'load_draft', '下書き (QuestionDraft)\n読み込み', 'db')
    add_node(g, 'has_draft', '下書きがあるか?', 'decision')
    add_node(g, 'prefill', 'フォームに\n下書き内容をセット', 'action')
    add_node(g, 'show_form', 'フォーム表示\n(タイトル/教科/本文/公開範囲)', 'frontend')
    add_node(g, 'submit', 'POST 送信', 'frontend')
    add_node(g, 'validate', 'QuestionForm\nバリデーション', 'action')
    add_node(g, 'valid', 'バリデーション\n成功か?', 'decision')
    add_node(g, 'show_errors', 'エラー表示', 'frontend')
    add_node(g, 'check_group', '投稿グループを\n選択しているか?', 'decision')
    add_node(g, 'validate_group', '選択グループの存在確認\n+ メンバーシップ確認', 'action')
    add_node(g, 'save_question', 'Question レコード保存', 'db')
    add_node(g, 'save_media', 'QuestionMedia 保存\n(添付ファイル, ≤100MB)', 'db')
    add_node(g, 'delete_draft', 'QuestionDraft 削除', 'db')
    add_node(g, 'check_ai', 'AI使用回数\n≤100回/日?', 'decision')
    add_node(g, 'dispatch_ai', 'Celery Task\n(非同期タスク)\ngenerate_ai_answer.delay()', 'async')
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
# 9. ユーザ登録
# =====================================================================
def create_registration_flow():
    g = new_graph('registration', 'ユーザ登録 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'firebase_auth', 'Firebase認証完了\n(Google / メールリンク)', 'external')
    add_node(g, 'post_token', 'POST /accounts/\nfirebase/callback/\n{idToken}', 'api')
    add_node(g, 'verify', 'verify_id_token()\nuid, email, name 抽出', 'action')
    add_node(g, 'find_user', 'User検索\n(firebase_uid\n→ email fallback)', 'db')
    add_node(g, 'exists', 'ユーザ\n存在する?', 'decision')
    add_node(g, 'login_existing', '既存ユーザ → login()\nJSON {action: "login"}', 'action')
    add_node(g, 'store_session', 'セッションに保存\nfirebase_uid\nfirebase_email\nfirebase_name', 'action')
    add_node(g, 'json_register', 'JSON {action: "register"\nredirect: "/accounts/register/"}', 'api')
    add_node(g, 'register_page', 'GET /accounts/register/\nセッションからemail取得\nフォーム表示', 'frontend')
    add_node(g, 'check_session', 'セッションに\nfirebase_email\nあるか?', 'decision')
    add_node(g, 'redirect_login', 'ログイン画面へ\nリダイレクト', 'frontend')
    add_node(g, 'fill_form', 'ユーザ名入力\nemail自動入力(hidden)', 'frontend')
    add_node(g, 'submit', 'POST 送信', 'frontend')
    add_node(g, 'validate', 'RegisterForm\nバリデーション', 'action')
    add_node(g, 'valid', 'バリデーション\n成功?', 'decision')
    add_node(g, 'show_errors', 'エラー表示', 'frontend')
    add_node(g, 'clean_email', 'clean_email()\n未検証ユーザ削除\nメール重複チェック', 'action')
    add_node(g, 'clear_deleted', '削除済みユーザの\nfirebase_uid クリア\n(一意制約解放)', 'db')
    add_node(g, 'create_user', 'User作成\nfirebase_uid紐付け\nis_verified=True\nset_unusable_password()', 'db')
    add_node(g, 'clear_session', 'セッションから\nFirebase情報削除', 'action')
    add_node(g, 'login_new', 'Django login()\nセッション作成', 'action')
    add_node(g, 'redirect_home', 'ホームへ\nリダイレクト', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'firebase_auth')
    g.edge('firebase_auth', 'post_token')
    g.edge('post_token', 'verify')
    g.edge('verify', 'find_user')
    g.edge('find_user', 'exists')
    g.edge('exists', 'login_existing', label='Yes')
    g.edge('login_existing', 'redirect_home')
    g.edge('exists', 'store_session', label='No')
    g.edge('store_session', 'json_register')
    g.edge('json_register', 'register_page')
    g.edge('register_page', 'check_session')
    g.edge('check_session', 'redirect_login', label='No')
    g.edge('check_session', 'fill_form', label='Yes')
    g.edge('fill_form', 'submit')
    g.edge('submit', 'validate')
    g.edge('validate', 'valid')
    g.edge('valid', 'show_errors', label='No')
    g.edge('show_errors', 'fill_form')
    g.edge('valid', 'clean_email', label='Yes')
    g.edge('clean_email', 'clear_deleted')
    g.edge('clear_deleted', 'create_user')
    g.edge('create_user', 'clear_session')
    g.edge('clear_session', 'login_new')
    g.edge('login_new', 'redirect_home')
    g.edge('redirect_home', 'end')

    save(g, '09_user_registration')


# =====================================================================
# 10. 質問検索・絞り込み
# =====================================================================
def create_search_filter_flow():
    g = new_graph('search', '質問検索・絞り込み 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'access', 'GET /questions/\n質問一覧ページ', 'frontend')
    add_node(g, 'get_groups', 'ユーザ所属グループ\nGroupMembership取得', 'db')
    add_node(g, 'base_query', 'ベースクエリ構築\nQ(public) |\nQ(group, user_groups) |\nQ(user=self)', 'action')
    add_node(g, 'has_subject', '教科フィルタ\nあり?', 'decision')
    add_node(g, 'filter_subject', '.filter(\nsubject_id=...)', 'action')
    add_node(g, 'has_username', 'ユーザ名検索\nあり?', 'decision')
    add_node(g, 'filter_username', '.filter(user__\nusername__icontains)', 'action')
    add_node(g, 'has_unresolved', '未解決のみ\nフィルタ?', 'decision')
    add_node(g, 'filter_unresolved', '.filter(\nis_resolved=False)', 'action')
    add_node(g, 'sort', 'ソート適用\n更新順(default)\n/ 名前順', 'action')
    add_node(g, 'paginate', 'Paginator\n20件/ページ', 'action')
    add_node(g, 'load_subjects', 'Subject一覧取得\n(フィルタ用)', 'db')
    add_node(g, 'is_htmx', 'htmx\nリクエスト?', 'decision')
    add_node(g, 'render_partial', '部分テンプレート\npartials/\nquestion_list.html', 'frontend')
    add_node(g, 'render_full', '完全テンプレート\nquestions/list.html', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'access')
    g.edge('access', 'get_groups')
    g.edge('get_groups', 'base_query')
    g.edge('base_query', 'has_subject')
    g.edge('has_subject', 'filter_subject', label='Yes')
    g.edge('has_subject', 'has_username', label='No')
    g.edge('filter_subject', 'has_username')
    g.edge('has_username', 'filter_username', label='Yes')
    g.edge('has_username', 'has_unresolved', label='No')
    g.edge('filter_username', 'has_unresolved')
    g.edge('has_unresolved', 'filter_unresolved', label='Yes')
    g.edge('has_unresolved', 'sort', label='No')
    g.edge('filter_unresolved', 'sort')
    g.edge('sort', 'paginate')
    g.edge('paginate', 'load_subjects')
    g.edge('load_subjects', 'is_htmx')
    g.edge('is_htmx', 'render_partial', label='Yes')
    g.edge('is_htmx', 'render_full', label='No')
    g.edge('render_partial', 'end')
    g.edge('render_full', 'end')

    save(g, '10_search_filter')


# =====================================================================
# 11. リアクション（👍👎）
# =====================================================================
def create_reaction_flow():
    g = new_graph('reaction', 'リアクション（👍👎） 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'click', 'リアクションボタン\nクリック\n(👍 or 👎)', 'frontend')
    add_node(g, 'post', 'POST /api/reactions/\n{answer_id,\nemoji_type}', 'api')
    add_node(g, 'find_answer', 'Answer検索\n(pk, is_deleted=False)', 'db')
    add_node(g, 'found', '回答\n存在する?', 'decision')
    add_node(g, 'error_404', '404 エラー', 'frontend')
    add_node(g, 'get_or_create', 'Reaction\nget_or_create\n(answer, user,\nemoji_type)', 'db')
    add_node(g, 'created', '新規作成?', 'decision')
    add_node(g, 'active_true', 'active=True\n(リアクション追加)', 'action')
    add_node(g, 'delete_reaction', 'reaction.delete()\nactive=False\n(リアクション取消)', 'db')
    add_node(g, 'count', '各emoji_type\nカウント集計', 'db')
    add_node(g, 'response', 'JSON応答\n{active,\ncounts: {👍:N, 👎:N}}', 'api')
    add_node(g, 'update_ui', 'ボタン表示更新\nカウント数反映\nアクティブ状態変更', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'click')
    g.edge('click', 'post')
    g.edge('post', 'find_answer')
    g.edge('find_answer', 'found')
    g.edge('found', 'error_404', label='No')
    g.edge('found', 'get_or_create', label='Yes')
    g.edge('get_or_create', 'created')
    g.edge('created', 'active_true', label='Yes (新規)')
    g.edge('created', 'delete_reaction', label='No (既存)')
    g.edge('active_true', 'count')
    g.edge('delete_reaction', 'count')
    g.edge('count', 'response')
    g.edge('response', 'update_ui')
    g.edge('update_ui', 'end')

    save(g, '11_reaction')


# =====================================================================
# 12. 下書き自動保存
# =====================================================================
def create_draft_flow():
    g = new_graph('draft', '下書き自動保存 処理フロー')

    # --- 質問下書き ---
    with g.subgraph(name='cluster_q_draft') as c:
        c.attr(label='<<B>質問 下書き保存</B>>', style='rounded,filled', color='#2980B9', fillcolor='#EBF5FB')
        add_node(c, 'qd_start', '開始', 'start')
        add_node(c, 'qd_create', '質問作成画面表示\nQuestionDraft読込', 'frontend')
        add_node(c, 'qd_has_draft', '下書き\nあり?', 'decision')
        add_node(c, 'qd_restore', 'フォームに\n下書き復元', 'action')
        add_node(c, 'qd_edit', 'ユーザが\nフォーム編集', 'frontend')
        add_node(c, 'qd_timer', '30秒タイマー\n発火', 'async')
        add_node(c, 'qd_post', 'POST /api/drafts/\nquestion/\n{title, subject_id,\nbody, body_format}', 'api')
        add_node(c, 'qd_upsert', 'QuestionDraft\nupdate_or_create', 'db')
        add_node(c, 'qd_saved', '"保存済み" 表示\n{saved_at}', 'frontend')
        add_node(c, 'qd_submit', '質問を投稿', 'frontend')
        add_node(c, 'qd_delete', 'QuestionDraft\n削除', 'db')

        c.edge('qd_start', 'qd_create')
        c.edge('qd_create', 'qd_has_draft')
        c.edge('qd_has_draft', 'qd_restore', label='Yes')
        c.edge('qd_has_draft', 'qd_edit', label='No')
        c.edge('qd_restore', 'qd_edit')
        c.edge('qd_edit', 'qd_timer')
        c.edge('qd_timer', 'qd_post')
        c.edge('qd_post', 'qd_upsert')
        c.edge('qd_upsert', 'qd_saved')
        c.edge('qd_saved', 'qd_edit', label='継続編集')
        c.edge('qd_edit', 'qd_submit', label='投稿')
        c.edge('qd_submit', 'qd_delete')

    # --- 回答下書き ---
    with g.subgraph(name='cluster_a_draft') as c:
        c.attr(label='<<B>回答 下書き保存</B>>', style='rounded,filled', color='#27AE60', fillcolor='#E8F8F5')
        add_node(c, 'ad_start', '開始', 'start')
        add_node(c, 'ad_create', '回答作成画面表示\nAnswerDraft読込', 'frontend')
        add_node(c, 'ad_has_draft', '下書き\nあり?', 'decision')
        add_node(c, 'ad_restore', 'フォームに\n下書き復元', 'action')
        add_node(c, 'ad_edit', 'ユーザが\nフォーム編集', 'frontend')
        add_node(c, 'ad_timer', '30秒タイマー\n発火', 'async')
        add_node(c, 'ad_post', 'POST /api/drafts/\nanswer/\n{question_id,\nbody, body_format}', 'api')
        add_node(c, 'ad_upsert', 'AnswerDraft\nupdate_or_create', 'db')
        add_node(c, 'ad_saved', '"保存済み" 表示', 'frontend')
        add_node(c, 'ad_submit', '回答を投稿', 'frontend')
        add_node(c, 'ad_delete', 'AnswerDraft\n削除', 'db')

        c.edge('ad_start', 'ad_create')
        c.edge('ad_create', 'ad_has_draft')
        c.edge('ad_has_draft', 'ad_restore', label='Yes')
        c.edge('ad_has_draft', 'ad_edit', label='No')
        c.edge('ad_restore', 'ad_edit')
        c.edge('ad_edit', 'ad_timer')
        c.edge('ad_timer', 'ad_post')
        c.edge('ad_post', 'ad_upsert')
        c.edge('ad_upsert', 'ad_saved')
        c.edge('ad_saved', 'ad_edit', label='継続編集')
        c.edge('ad_edit', 'ad_submit', label='投稿')
        c.edge('ad_submit', 'ad_delete')

    save(g, '12_draft_autosave')


# =====================================================================
# 13. エクスポート (CSV/XLSX/PDF/Markdown/TXT)
# =====================================================================
def create_export_flow():
    g = new_graph('export', 'エクスポート 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'click', 'エクスポートボタン\nドロップダウン選択', 'frontend')
    add_node(g, 'request', 'GET /questions/<pk>/\nexport/?format=<fmt>', 'api')
    add_node(g, 'load', 'Question +\nAnswers 読込\n(select_related)', 'db')
    add_node(g, 'format', 'フォーマット\n判定', 'decision')

    add_node(g, 'csv', 'export_csv()\nstdlib csv\n質問+各回答を行出力', 'action')
    add_node(g, 'xlsx', 'export_xlsx()\nopenpyxl\n2シート: 質問 + 回答', 'action')
    add_node(g, 'pdf', 'export_pdf()\nWeasyPrint\nHTML→PDF変換\n日本語フォント対応', 'action')
    add_node(g, 'md', 'export_markdown()\nAI回答はhtml_to_text()\nで変換', 'action')
    add_node(g, 'txt', 'export_txt()\nプレーンテキスト\n出力', 'action')

    add_node(g, 'response', 'HttpResponse\nContent-Disposition:\nattachment; filename=...', 'api')
    add_node(g, 'download', 'ファイル\nダウンロード', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'click')
    g.edge('click', 'request')
    g.edge('request', 'load')
    g.edge('load', 'format')
    g.edge('format', 'csv', label='csv')
    g.edge('format', 'xlsx', label='xlsx')
    g.edge('format', 'pdf', label='pdf')
    g.edge('format', 'md', label='md')
    g.edge('format', 'txt', label='txt')
    g.edge('csv', 'response')
    g.edge('xlsx', 'response')
    g.edge('pdf', 'response')
    g.edge('md', 'response')
    g.edge('txt', 'response')
    g.edge('response', 'download')
    g.edge('download', 'end')

    save(g, '13_export')


# =====================================================================
# 14. サンドボックス回答表示 (Shadow DOM / iframe)
# =====================================================================
def create_sandbox_flow():
    g = new_graph('sandbox', 'サンドボックス回答表示 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'detail', '質問詳細ページ\n読み込み', 'frontend')
    add_node(g, 'gen_token', 'generate_token()\nHMAC-SHA256\n(answer_id + SECRET_KEY)', 'action')
    add_node(g, 'sanitize', 'sanitize_ai_html()\nintegrity属性除去\nDOCTYPE/html/head除去\n未閉じタグ補完', 'action')
    add_node(g, 'is_ai', 'AI回答?', 'decision')

    # Shadow DOM path
    add_node(g, 'init_shadow', 'initShadowDOM()\nShadow Root作成\nmode: open', 'frontend')
    add_node(g, 'inject_html', '消毒済みHTML\nShadow DOMに挿入', 'frontend')
    add_node(g, 'exec_scripts', 'スクリプト再実行\n(mermaid.initialize除去\n関数をwindowに公開)', 'action')
    add_node(g, 'render_libs', 'KaTeX / Mermaid /\nChart.js レンダリング', 'frontend')

    # iframe fallback
    add_node(g, 'iframe_req', 'iframe src=\ncontent.sirisa.net\n/content/answer/<pk>/', 'frontend')
    add_node(g, 'verify_token', 'verify_token()\nHMAC検証', 'action')
    add_node(g, 'valid_token', 'トークン\n有効?', 'decision')
    add_node(g, 'reject', '403 Forbidden', 'frontend')
    add_node(g, 'rewrite_links', '_rewrite_links()\n外部リンクを\nクッションページに変換', 'action')
    add_node(g, 'set_csp', 'CSP ヘッダ設定\njsdelivr/cdnjs許可\nX-Frame-Options:\nALLOWALL', 'action')
    add_node(g, 'render_iframe', 'iframe内\nHTML描画', 'frontend')

    # postMessage
    add_node(g, 'post_msg', 'postMessage通信\nresize / textSelected /\ntheme / highlightText', 'api')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'detail')
    g.edge('detail', 'gen_token')
    g.edge('gen_token', 'sanitize')
    g.edge('sanitize', 'is_ai')
    g.edge('is_ai', 'init_shadow', label='Yes\n(Shadow DOM)')
    g.edge('is_ai', 'iframe_req', label='No\n(ユーザ回答)')

    # Shadow DOM flow
    g.edge('init_shadow', 'inject_html')
    g.edge('inject_html', 'exec_scripts')
    g.edge('exec_scripts', 'render_libs')
    g.edge('render_libs', 'post_msg')

    # iframe flow
    g.edge('iframe_req', 'verify_token')
    g.edge('verify_token', 'valid_token')
    g.edge('valid_token', 'reject', label='No')
    g.edge('valid_token', 'rewrite_links', label='Yes')
    g.edge('rewrite_links', 'set_csp')
    g.edge('set_csp', 'render_iframe')
    g.edge('render_iframe', 'post_msg')

    g.edge('post_msg', 'end')

    save(g, '14_sandbox_display')


# =====================================================================
# 15. 外部リンク Safe Browsing (クッションページ)
# =====================================================================
def create_cushion_flow():
    g = new_graph('cushion', '外部リンク Safe Browsing 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'ai_answer', 'AI回答表示', 'frontend')
    add_node(g, 'rewrite', '_rewrite_links()\nhref="https://..."を\n/cushion/?url=<encoded>\nに書き換え', 'action')
    add_node(g, 'skip_safe', '安全ドメイン?\nsirisa.net\njsdelivr, cdnjs,\ngoogleapis等', 'decision')
    add_node(g, 'keep_link', 'リンクそのまま\n(書き換えなし)', 'action')
    add_node(g, 'click', 'ユーザが\n外部リンクをクリック', 'frontend')
    add_node(g, 'cushion_view', 'GET /content/cushion/\n?url=<encoded>', 'api')
    add_node(g, 'call_api', 'Google Safe\nBrowsing API v4\nPOST threatMatches:find', 'external')
    add_node(g, 'timeout', 'タイムアウト\n5秒', 'decision')
    add_node(g, 'default_safe', '安全と判定\n(デフォルト)', 'action')
    add_node(g, 'check_threat', '脅威\n検出?', 'decision')
    add_node(g, 'show_safe', '緑アラート\n"安全と判定"\n外部サイトへ遷移ボタン', 'frontend')
    add_node(g, 'show_unsafe', '赤アラート\n脅威名表示\n(マルウェア/\nフィッシング等)', 'frontend')
    add_node(g, 'user_choice', 'ユーザ選択\n遷移 or 戻る', 'decision')
    add_node(g, 'navigate', '外部サイトへ\nrel="noopener\nnoreferrer"\ntarget="_blank"', 'frontend')
    add_node(g, 'go_back', '前のページに\n戻る', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'ai_answer')
    g.edge('ai_answer', 'rewrite')
    g.edge('rewrite', 'skip_safe')
    g.edge('skip_safe', 'keep_link', label='Yes')
    g.edge('skip_safe', 'click', label='No')
    g.edge('keep_link', 'end')
    g.edge('click', 'cushion_view')
    g.edge('cushion_view', 'call_api')
    g.edge('call_api', 'timeout')
    g.edge('timeout', 'default_safe', label='タイムアウト')
    g.edge('timeout', 'check_threat', label='応答あり')
    g.edge('default_safe', 'show_safe')
    g.edge('check_threat', 'show_safe', label='安全')
    g.edge('check_threat', 'show_unsafe', label='脅威あり')
    g.edge('show_safe', 'user_choice')
    g.edge('show_unsafe', 'user_choice')
    g.edge('user_choice', 'navigate', label='遷移')
    g.edge('user_choice', 'go_back', label='戻る')
    g.edge('navigate', 'end')
    g.edge('go_back', 'end')

    save(g, '15_safe_browsing')


# =====================================================================
# 16. プロフィール編集
# =====================================================================
def create_profile_flow():
    g = new_graph('profile', 'プロフィール編集 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'access', 'GET /accounts/profile/\nプロフィール画面', 'frontend')
    add_node(g, 'load_forms', 'ProfileForm +\nEmailChangeForm\n生成', 'action')
    add_node(g, 'mask_email', '_mask_email()\n"k.noguchi@..."→\n"k*******@..."', 'action')
    add_node(g, 'show', 'プロフィール表示\n(ユーザ名/職業/所属/\n学年/年齢/自己紹介)', 'frontend')
    add_node(g, 'action', '操作選択', 'decision')

    # プロフィール更新
    add_node(g, 'edit_profile', 'POST プロフィール\n更新', 'frontend')
    add_node(g, 'validate_p', 'ProfileForm\nバリデーション', 'action')
    add_node(g, 'valid_p', '成功?', 'decision')
    add_node(g, 'save_profile', 'User.save()\nプロフィール更新', 'db')
    add_node(g, 'error_p', 'エラー表示', 'frontend')

    # メール変更
    add_node(g, 'change_email', 'POST メール\nアドレス変更', 'frontend')
    add_node(g, 'validate_e', 'EmailChangeForm\nバリデーション\n(重複チェック)', 'action')
    add_node(g, 'valid_e', '成功?', 'decision')
    add_node(g, 'save_email', 'User.email更新\nsave(update_fields=\n["email"])', 'db')
    add_node(g, 'error_e', 'エラー表示', 'frontend')

    add_node(g, 'redirect', 'リダイレクト\n成功メッセージ', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'access')
    g.edge('access', 'load_forms')
    g.edge('load_forms', 'mask_email')
    g.edge('mask_email', 'show')
    g.edge('show', 'action')
    g.edge('action', 'edit_profile', label='プロフィール')
    g.edge('action', 'change_email', label='メール変更')
    g.edge('edit_profile', 'validate_p')
    g.edge('validate_p', 'valid_p')
    g.edge('valid_p', 'save_profile', label='Yes')
    g.edge('valid_p', 'error_p', label='No')
    g.edge('error_p', 'show')
    g.edge('save_profile', 'redirect')
    g.edge('change_email', 'validate_e')
    g.edge('validate_e', 'valid_e')
    g.edge('valid_e', 'save_email', label='Yes')
    g.edge('valid_e', 'error_e', label='No')
    g.edge('error_e', 'show')
    g.edge('save_email', 'redirect')
    g.edge('redirect', 'end')

    save(g, '16_profile_edit')


# =====================================================================
# 17. アカウント削除（匿名化）
# =====================================================================
def create_account_delete_flow():
    g = new_graph('account_delete', 'アカウント削除（匿名化） 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'access', 'プロフィール画面\n"アカウント削除"\nボタン', 'frontend')
    add_node(g, 'confirm', '確認ダイアログ', 'frontend')
    add_node(g, 'post', 'POST /accounts/\nprofile/delete/', 'api')
    add_node(g, 'anonymize', 'anonymize_for_deletion()', 'action')
    add_node(g, 'gen_suffix', 'UUID生成\nuuid4().hex[:12]', 'action')
    add_node(g, 'set_anon', 'email → deleted_xxx\n@deleted.local\nusername → deleted_xxx', 'action')
    add_node(g, 'set_flags', 'is_deleted = True\nis_active = False\ndeleted_at = now()', 'action')
    add_node(g, 'save_user', 'User.save()\n匿名化データ保存', 'db')
    add_node(g, 'logout', 'Django logout()\nセッション破棄', 'action')
    add_node(g, 'redirect', 'ログイン画面へ\nリダイレクト\n"アカウントを\n削除しました"', 'frontend')
    add_node(g, 'end', '終了', 'end')

    # 再登録フロー
    add_node(g, 'reregister', '同一Firebase UID\nで再登録時', 'action')
    add_node(g, 'clear_uid', 'firebase_uid クリア\n(一意制約解放)\nUPDATE SET\nfirebase_uid=NULL', 'db')

    g.edge('start', 'access')
    g.edge('access', 'confirm')
    g.edge('confirm', 'post')
    g.edge('post', 'anonymize')
    g.edge('anonymize', 'gen_suffix')
    g.edge('gen_suffix', 'set_anon')
    g.edge('set_anon', 'set_flags')
    g.edge('set_flags', 'save_user')
    g.edge('save_user', 'logout')
    g.edge('logout', 'redirect')
    g.edge('redirect', 'end')

    # 再登録の補足
    g.edge('save_user', 'reregister', style='dashed', color='#8E44AD', label='将来')
    g.edge('reregister', 'clear_uid', style='dashed', color='#8E44AD')

    save(g, '17_account_delete')


# =====================================================================
# 18. ユーザ通報
# =====================================================================
def create_user_report_flow():
    g = new_graph('report', 'ユーザ通報 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'view_profile', '他ユーザの\nプロフィール表示', 'frontend')
    add_node(g, 'click_report', '"通報" ボタン\nクリック', 'frontend')
    add_node(g, 'show_form', '通報フォーム表示\n理由: スパム/不適切/\n嫌がらせ/なりすまし/\nその他', 'frontend')
    add_node(g, 'submit', 'POST /accounts/\n<username>/report/', 'api')
    add_node(g, 'find_target', 'User検索\n(username,\nis_deleted=False)', 'db')
    add_node(g, 'self_check', '自分自身へ\nの通報?', 'decision')
    add_node(g, 'self_error', 'エラー:\n自分自身は\n通報できません', 'frontend')
    add_node(g, 'rate_check', '24時間以内に\n同一ユーザを\n通報済み?', 'decision')
    add_node(g, 'rate_error', 'エラー:\n24時間に\n1回まで', 'frontend')
    add_node(g, 'validate', 'UserReportForm\nバリデーション', 'action')
    add_node(g, 'valid', '成功?', 'decision')
    add_node(g, 'form_error', 'フォーム\nエラー表示', 'frontend')
    add_node(g, 'create_report', 'UserReport作成\n(reporter,\nreported_user,\nreason, detail)', 'db')
    add_node(g, 'redirect', 'リダイレクト\nプロフィール画面\n成功メッセージ', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'view_profile')
    g.edge('view_profile', 'click_report')
    g.edge('click_report', 'show_form')
    g.edge('show_form', 'submit')
    g.edge('submit', 'find_target')
    g.edge('find_target', 'self_check')
    g.edge('self_check', 'self_error', label='Yes')
    g.edge('self_error', 'view_profile')
    g.edge('self_check', 'rate_check', label='No')
    g.edge('rate_check', 'rate_error', label='Yes')
    g.edge('rate_error', 'view_profile')
    g.edge('rate_check', 'validate', label='No')
    g.edge('validate', 'valid')
    g.edge('valid', 'form_error', label='No')
    g.edge('form_error', 'show_form')
    g.edge('valid', 'create_report', label='Yes')
    g.edge('create_report', 'redirect')
    g.edge('redirect', 'end')

    save(g, '18_user_report')


# =====================================================================
# 19. 質問編集
# =====================================================================
def create_question_edit_flow():
    g = new_graph('question_edit', '質問編集 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'access', 'GET /questions/<pk>/edit/\n所有者チェック', 'frontend')
    add_node(g, 'load', 'Question +\nQuestionMedia +\nAnswers 読込', 'db')
    add_node(g, 'show_form', 'QuestionForm\n(タイトル/教科/本文)\n+ 既存メディア一覧', 'frontend')
    add_node(g, 'submit', 'POST 送信', 'frontend')
    add_node(g, 'validate', 'QuestionForm\nバリデーション', 'action')
    add_node(g, 'valid', '成功?', 'decision')
    add_node(g, 'show_errors', 'エラー表示', 'frontend')
    add_node(g, 'save_question', 'Question.save()\n更新', 'db')
    add_node(g, 'has_delete', '削除対象\nメディアあり?', 'decision')
    add_node(g, 'soft_delete', 'media.soft_delete()\n+ DeletionLog記録', 'db')
    add_node(g, 'has_new', '新規ファイル\nあり?', 'decision')
    add_node(g, 'check_size', '合計サイズ\n≤ 100MB?', 'decision')
    add_node(g, 'size_error', 'サイズ超過\nエラー', 'frontend')
    add_node(g, 'save_media', 'QuestionMedia\n作成', 'db')
    add_node(g, 'redirect', 'リダイレクト\n質問詳細\n成功メッセージ', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'access')
    g.edge('access', 'load')
    g.edge('load', 'show_form')
    g.edge('show_form', 'submit')
    g.edge('submit', 'validate')
    g.edge('validate', 'valid')
    g.edge('valid', 'show_errors', label='No')
    g.edge('show_errors', 'show_form')
    g.edge('valid', 'save_question', label='Yes')
    g.edge('save_question', 'has_delete')
    g.edge('has_delete', 'soft_delete', label='Yes')
    g.edge('has_delete', 'has_new', label='No')
    g.edge('soft_delete', 'has_new')
    g.edge('has_new', 'check_size', label='Yes')
    g.edge('has_new', 'redirect', label='No')
    g.edge('check_size', 'size_error', label='No')
    g.edge('size_error', 'show_form')
    g.edge('check_size', 'save_media', label='Yes')
    g.edge('save_media', 'redirect')
    g.edge('redirect', 'end')

    save(g, '19_question_edit')


# =====================================================================
# 20. 自動補完 (AutoSupplement)
# =====================================================================
def create_supplement_flow():
    g = new_graph('supplement', '自動補完 (AutoSupplement) 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'trigger', 'フロントエンドから\n補完リクエスト', 'frontend')
    add_node(g, 'post', 'POST /api/supplements/\n{body,\nsubject_name}', 'api')
    add_node(g, 'parse', 'JSONパース\nbody必須チェック', 'action')
    add_node(g, 'check_limit', 'AIUsageLog\ncan_use()?', 'decision')
    add_node(g, 'limit_error', '429 Too Many\nRequests', 'api')
    add_node(g, 'increment', 'AIUsageLog\nincrement()', 'db')
    add_node(g, 'call_gemini', 'Vertex AI\nGemini 2.5 Flash\ngenerate_supplements()\ntemp=0.3, max=2048', 'external')
    add_node(g, 'parse_json', 'レスポンスJSON解析\nコードフェンス除去', 'action')
    add_node(g, 'response', 'JSON応答\n{supplements:\n[{text, type,\nexplanation}]}', 'api')
    add_node(g, 'display', '用語リスト表示\n最大5件の\n補完情報', 'frontend')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'trigger')
    g.edge('trigger', 'post')
    g.edge('post', 'parse')
    g.edge('parse', 'check_limit')
    g.edge('check_limit', 'limit_error', label='No')
    g.edge('check_limit', 'increment', label='Yes')
    g.edge('increment', 'call_gemini')
    g.edge('call_gemini', 'parse_json')
    g.edge('parse_json', 'response')
    g.edge('response', 'display')
    g.edge('display', 'end')

    save(g, '20_auto_supplement')


# =====================================================================
# 21. AI使用回数制限
# =====================================================================
def create_ai_usage_limit_flow():
    g = new_graph('ai_limit', 'AI使用回数制限 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'request', 'AI機能リクエスト\n(回答/返信/注釈/補完)', 'frontend')
    add_node(g, 'can_use', 'AIUsageLog.can_use()\nユーザの今日の\n使用回数チェック', 'action')
    add_node(g, 'get_today', 'get_or_create\n(user, date=today)\n→ usage_count', 'db')
    add_node(g, 'check', 'usage_count\n< 100?', 'decision')
    add_node(g, 'reject', '制限超過\n各機能で処理分岐', 'action')

    # 各機能の制限時動作
    add_node(g, 'r_answer', 'AI回答: タスク\nスキップ (警告表示)', 'frontend')
    add_node(g, 'r_reply', 'AI返信: @ai\n無視', 'action')
    add_node(g, 'r_annotation', 'AI注釈: 429\nJSONエラー', 'api')
    add_node(g, 'r_supplement', 'AI補完: 429\nJSONエラー', 'api')

    add_node(g, 'allow', 'AI処理実行', 'action')
    add_node(g, 'increment', 'AIUsageLog.increment()\nF("usage_count")+1\n(アトミック更新)', 'db')
    add_node(g, 'remaining', 'AIUsageLog.remaining()\nmax(0, 100 - count)\n→ 残回数表示', 'action')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'request')
    g.edge('request', 'can_use')
    g.edge('can_use', 'get_today')
    g.edge('get_today', 'check')
    g.edge('check', 'reject', label='No (≥100)')
    g.edge('reject', 'r_answer', label='AI回答')
    g.edge('reject', 'r_reply', label='AI返信')
    g.edge('reject', 'r_annotation', label='AI注釈')
    g.edge('reject', 'r_supplement', label='AI補完')
    g.edge('check', 'allow', label='Yes (<100)')
    g.edge('allow', 'increment')
    g.edge('increment', 'remaining')
    g.edge('remaining', 'end')
    g.edge('r_answer', 'end')
    g.edge('r_reply', 'end')
    g.edge('r_annotation', 'end')
    g.edge('r_supplement', 'end')

    save(g, '21_ai_usage_limit')


# =====================================================================
# 22. メディアアップロード
# =====================================================================
def create_media_upload_flow():
    g = new_graph('media', 'メディアアップロード 処理フロー')

    add_node(g, 'start', '開始', 'start')
    add_node(g, 'select_files', 'ファイル選択\n(input type=file)', 'frontend')
    add_node(g, 'submit', 'フォーム送信\n(質問/回答/返信)', 'frontend')
    add_node(g, 'get_files', 'request.FILES\n.getlist()', 'action')
    add_node(g, 'validate_ext', 'FileExtension\nValidator\njpg/png/gif/webp/svg\nmp3/wav/ogg/m4a\nmp4/webm/mov/avi\npdf/doc/docx/txt', 'action')
    add_node(g, 'valid_ext', '拡張子\n有効?', 'decision')
    add_node(g, 'ext_error', '拡張子エラー', 'frontend')
    add_node(g, 'check_size', '合計サイズ\n≤ 100MB?', 'decision')
    add_node(g, 'size_error', 'サイズ超過\nエラー', 'frontend')
    add_node(g, 'detect_type', '_detect_media_type()\nimage / audio /\nvideo / other\n(拡張子から判定)', 'action')
    add_node(g, 'save_model', 'QuestionMedia /\nAnswerMedia /\nReplyMedia 作成', 'db')
    add_node(g, 'set_fields', 'auto保存:\nfile_size\noriginal_name\nmedia_type', 'action')
    add_node(g, 'upload_path', 'ファイル保存\nquestions/{pk}/\nanswers/{pk}/\nreplies/{pk}/', 'db')
    add_node(g, 'ai_input', 'AIマルチモーダル\n入力? (質問のみ)', 'decision')
    add_node(g, 'part_data', 'Part.from_data()\nMIME判定\n→ Gemini入力', 'external')
    add_node(g, 'end', '終了', 'end')

    g.edge('start', 'select_files')
    g.edge('select_files', 'submit')
    g.edge('submit', 'get_files')
    g.edge('get_files', 'validate_ext')
    g.edge('validate_ext', 'valid_ext')
    g.edge('valid_ext', 'ext_error', label='No')
    g.edge('valid_ext', 'check_size', label='Yes')
    g.edge('check_size', 'size_error', label='No')
    g.edge('check_size', 'detect_type', label='Yes')
    g.edge('detect_type', 'save_model')
    g.edge('save_model', 'set_fields')
    g.edge('set_fields', 'upload_path')
    g.edge('upload_path', 'ai_input')
    g.edge('ai_input', 'part_data', label='Yes')
    g.edge('ai_input', 'end', label='No')
    g.edge('part_data', 'end')

    save(g, '22_media_upload')


# =====================================================================
# A. システムアーキテクチャ
# =====================================================================
def create_architecture_diagram():
    g = graphviz.Digraph('architecture', format='png')
    g.attr(
        rankdir='TB',
        fontname='Noto Sans CJK JP',
        fontsize='18',
        bgcolor='#FAFBFC',
        pad='0.8',
        nodesep='0.6',
        ranksep='0.8',
        dpi='150',
        label='<<B>SIRISA システムアーキテクチャ</B>>',
        labelloc='t',
    )
    g.edge_attr.update(**EDGE_ATTR)

    # --- クライアント層 ---
    with g.subgraph(name='cluster_client') as c:
        c.attr(label='<<B>クライアント層</B>>', style='rounded,filled', color='#E67E22', fillcolor='#FFF5EB')
        c.node('browser', 'ブラウザ\n(Desktop / Mobile)', shape='box', style='rounded,filled', fillcolor='#FDEBD0', color='#E67E22', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('frontend_stack', 'htmx / Bootstrap 5\nKaTeX / Mermaid.js\nChart.js / Shadow DOM', shape='box', style='rounded,filled', fillcolor='#FDEBD0', color='#E67E22', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('firebase_sdk', 'Firebase Web SDK v10\n(Google / Email Link)', shape='box3d', style='filled', fillcolor='#FADBD8', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='9')
        c.edge('browser', 'frontend_stack', style='invis')
        c.edge('frontend_stack', 'firebase_sdk', style='invis')

    # --- Webサーバ層 ---
    with g.subgraph(name='cluster_web') as c:
        c.attr(label='<<B>Webサーバ層</B>>', style='rounded,filled', color='#3498DB', fillcolor='#EBF5FB')
        c.node('nginx', 'nginx\nHTTPS (Let\'s Encrypt)\nIP制限\n静的ファイル配信', shape='box', style='rounded,filled', fillcolor='#D6EAF8', color='#2980B9', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('domain_main', 'sirisa.net\n(メインアプリ)', shape='box', style='rounded,filled', fillcolor='#D6EAF8', color='#2980B9', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('domain_content', 'content.sirisa.net\n(サンドボックス)', shape='box', style='rounded,filled', fillcolor='#D6EAF8', color='#2980B9', fontname='Noto Sans CJK JP', fontsize='9')
        c.edge('nginx', 'domain_main', style='invis')
        c.edge('nginx', 'domain_content', style='invis')

    # --- アプリケーション層 ---
    with g.subgraph(name='cluster_app') as c:
        c.attr(label='<<B>アプリケーション層</B>>', style='rounded,filled', color='#27AE60', fillcolor='#E8F8F5')
        c.node('gunicorn', 'Gunicorn\n3 workers\nUnix Socket\n120s timeout', shape='box', style='rounded,filled', fillcolor='#D5F5E3', color='#27AE60', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('django', 'Django 4.2 LTS\nPython 3.12\nWSGI', shape='box', style='rounded,filled', fillcolor='#D5F5E3', color='#27AE60', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('middleware', 'Middleware\nSecurity / Session\nCSRF / Auth\nhtmx / XFrame', shape='box', style='rounded,filled', fillcolor='#D5F5E3', color='#27AE60', fontname='Noto Sans CJK JP', fontsize='9')

    # --- Django Apps ---
    with g.subgraph(name='cluster_apps') as c:
        c.attr(label='<<B>Django Apps</B>>', style='rounded,filled', color='#8E44AD', fillcolor='#F5EEF8')
        c.node('app_accounts', 'accounts\nFirebase Auth\nプロフィール\n通報', shape='box', style='rounded,filled', fillcolor='#E8DAEF', color='#8E44AD', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('app_questions', 'questions\nQ&A / AI回答\nリアクション\n下書き / エクスポート', shape='box', style='rounded,filled', fillcolor='#E8DAEF', color='#8E44AD', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('app_groups', 'groups\n小グループ\n招待コード', shape='box', style='rounded,filled', fillcolor='#E8DAEF', color='#8E44AD', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('app_content', 'content\nサンドボックス\nクッションページ', shape='box', style='rounded,filled', fillcolor='#E8DAEF', color='#8E44AD', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('app_core', 'core\nSoftDeleteMixin\nDeletionLog\nTimeStampMixin', shape='box', style='rounded,filled', fillcolor='#E8DAEF', color='#8E44AD', fontname='Noto Sans CJK JP', fontsize='9')

    # --- 非同期処理層 ---
    with g.subgraph(name='cluster_async') as c:
        c.attr(label='<<B>非同期処理層</B>>', style='rounded,filled', color='#E74C3C', fillcolor='#FDEDEC')
        c.node('celery', 'Celery Worker\n2 concurrency\ngenerate_ai_answer\ngenerate_ai_reply', shape='box', style='filled,dashed', fillcolor='#F5B7B1', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('redis', 'Redis\nBroker + Backend\nlocalhost:6379', shape='cylinder', style='filled', fillcolor='#F5B7B1', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='10')

    # --- データ層 ---
    with g.subgraph(name='cluster_data') as c:
        c.attr(label='<<B>データ層</B>>', style='rounded,filled', color='#1ABC9C', fillcolor='#E8F8F5')
        c.node('postgresql', 'PostgreSQL 16\nsirisa_db\nlocalhost:5432', shape='cylinder', style='filled', fillcolor='#D1F2EB', color='#1ABC9C', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('filesystem', 'ローカルFS\n/opt/sirisa/media/\nquestions/ answers/\nreplies/', shape='folder', style='filled', fillcolor='#D1F2EB', color='#1ABC9C', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('static', 'Static Files\n/opt/sirisa/\nstaticfiles/', shape='folder', style='filled', fillcolor='#D1F2EB', color='#1ABC9C', fontname='Noto Sans CJK JP', fontsize='10')

    # --- 外部サービス ---
    with g.subgraph(name='cluster_external') as c:
        c.attr(label='<<B>外部サービス</B>>', style='rounded,filled', color='#E74C3C', fillcolor='#FDEDEC')
        c.node('vertex_ai', 'Vertex AI\nGemini 2.5 Pro (回答)\nGemini 2.5 Flash\n(返信/注釈/補完)', shape='box3d', style='filled', fillcolor='#FADBD8', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('firebase_admin', 'Firebase Admin SDK\nID Token検証\nユーザ認証', shape='box3d', style='filled', fillcolor='#FADBD8', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('safe_browsing', 'Google Safe\nBrowsing API v4\nURL安全性チェック', shape='box3d', style='filled', fillcolor='#FADBD8', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('gmail_smtp', 'Gmail SMTP\nメール送信', shape='box3d', style='filled', fillcolor='#FADBD8', color='#E74C3C', fontname='Noto Sans CJK JP', fontsize='9')

    # --- インフラ ---
    with g.subgraph(name='cluster_infra') as c:
        c.attr(label='<<B>インフラ</B>>', style='rounded,filled', color='#566573', fillcolor='#F2F3F4')
        c.node('gce', 'Google Compute Engine\nIP: 34.28.41.172', shape='box3d', style='filled', fillcolor='#D5D8DC', color='#566573', fontname='Noto Sans CJK JP', fontsize='10')
        c.node('systemd', 'systemd\nsirisa.service\nsirisa-celery.service', shape='box', style='rounded,filled', fillcolor='#D5D8DC', color='#566573', fontname='Noto Sans CJK JP', fontsize='9')
        c.node('letsencrypt', 'Let\'s Encrypt\nSSL証明書\n(certbot)', shape='box', style='rounded,filled', fillcolor='#D5D8DC', color='#566573', fontname='Noto Sans CJK JP', fontsize='9')

    # ===== 接続 =====
    # クライアント → nginx
    g.edge('browser', 'nginx', label='HTTPS\n(443)')
    g.edge('firebase_sdk', 'firebase_admin', label='IDトークン', style='dashed', color='#E74C3C')

    # nginx → Gunicorn
    g.edge('nginx', 'gunicorn', label='Unix Socket')
    g.edge('nginx', 'static', label='直接配信', style='dashed')
    g.edge('nginx', 'filesystem', label='/media/ 配信', style='dashed')

    # Gunicorn → Django
    g.edge('gunicorn', 'django', label='WSGI')
    g.edge('django', 'middleware')

    # Middleware → Apps
    g.edge('middleware', 'app_accounts')
    g.edge('middleware', 'app_questions')
    g.edge('middleware', 'app_groups')
    g.edge('middleware', 'app_content')

    # Apps → DB
    g.edge('app_accounts', 'postgresql', label='ORM')
    g.edge('app_questions', 'postgresql', label='ORM')
    g.edge('app_groups', 'postgresql', label='ORM')
    g.edge('app_content', 'postgresql', label='ORM', style='dashed')

    # Apps → FS
    g.edge('app_questions', 'filesystem', label='メディア\n保存/読込')

    # Async
    g.edge('app_questions', 'celery', label='task.delay()', style='dashed', color='#E74C3C')
    g.edge('celery', 'redis', label='Broker')
    g.edge('celery', 'postgresql', label='結果保存')
    g.edge('celery', 'vertex_ai', label='AI生成\n(回答/返信)', color='#E74C3C')

    # External
    g.edge('app_accounts', 'firebase_admin', label='トークン\n検証', color='#E74C3C')
    g.edge('app_questions', 'vertex_ai', label='注釈/補完\n(同期)', color='#E74C3C', style='dashed')
    g.edge('app_content', 'safe_browsing', label='URL\nチェック', color='#E74C3C')

    # Infra
    g.edge('gce', 'systemd', style='invis')
    g.edge('gce', 'letsencrypt', style='invis')
    g.edge('systemd', 'gunicorn', label='管理', style='dotted')
    g.edge('systemd', 'celery', label='管理', style='dotted')
    g.edge('letsencrypt', 'nginx', label='SSL証明書', style='dotted')

    save(g, '00_architecture')


# =====================================================================
# メイン
# =====================================================================
def main():
    print('SIRISA 処理フロー図を生成中...\n')

    # アーキテクチャ
    create_architecture_diagram()

    # 既存8機能
    create_question_flow()
    create_answer_flow()
    create_reply_flow()
    create_ai_reply_flow()
    create_formula_flow()
    create_word_annotation_flow()
    create_group_flow()
    create_login_flow()

    # 追加14機能
    create_registration_flow()
    create_search_filter_flow()
    create_reaction_flow()
    create_draft_flow()
    create_export_flow()
    create_sandbox_flow()
    create_cushion_flow()
    create_profile_flow()
    create_account_delete_flow()
    create_user_report_flow()
    create_question_edit_flow()
    create_supplement_flow()
    create_ai_usage_limit_flow()
    create_media_upload_flow()

    total = 23  # 1 architecture + 22 features
    print(f'\n全{total}枚の図を {OUTPUT_DIR}/ に出力しました。')


if __name__ == '__main__':
    main()
