"""
SIRISA 質問・回答ビュー
"""
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.db.models import Q, Count
from django.utils import timezone
import markdown as md
import bleach

from .models import (
    Question, QuestionMedia, Answer, AnswerMedia,
    Reaction, Subject, QuestionDraft, AnswerDraft,
    Reply, AIAnnotation,
)
from .forms import QuestionForm, AnswerForm, ReplyForm
from .tasks import generate_ai_answer, generate_ai_reply
from . import export as export_module
from .utils import render_body

logger = logging.getLogger(__name__)

# メディアサイズ上限（100MB）
MAX_TOTAL_MEDIA_SIZE = 100 * 1024 * 1024


class HomeView(LoginRequiredMixin, View):
    """ホーム画面"""

    def get(self, request):
        from groups.models import GroupMembership
        user_group_ids = list(
            GroupMembership.objects.filter(user=request.user)
            .values_list('group_id', flat=True)
        )

        recent_questions = Question.objects.select_related(
            'user', 'subject'
        ).filter(
            Q(visibility='public') |
            Q(visibility='group', group_id__in=user_group_ids) |
            Q(user=request.user)
        ).order_by('-created_at')[:5]
        return render(request, 'questions/home.html', {
            'recent_questions': recent_questions,
        })


class QuestionCreateView(LoginRequiredMixin, View):
    """質問投稿画面"""

    def get(self, request):
        form = QuestionForm(user=request.user)
        # 既存の下書きを読み込み
        draft = QuestionDraft.objects.filter(
            user=request.user, question__isnull=True
        ).order_by('-auto_saved_at').first()
        if draft:
            form = QuestionForm(user=request.user, initial={
                'title': draft.title,
                'subject': draft.subject_id,
                'custom_subject': draft.custom_subject,
                'body': draft.body,
                'body_format': draft.body_format or 'text',
            })
        return render(request, 'questions/create.html', {'form': form})

    def post(self, request):
        form = QuestionForm(request.POST, user=request.user)
        if form.is_valid():
            question = form.save(commit=False)
            question.user = request.user

            # グループ共有
            visibility = form.cleaned_data.get('visibility', 'public')
            question.visibility = visibility
            if visibility == 'group':
                group_id = request.POST.get('group')
                if group_id:
                    from groups.models import StudyGroup, GroupMembership
                    try:
                        group = StudyGroup.objects.get(pk=group_id, is_active=True)
                        # メンバーチェック
                        if GroupMembership.objects.filter(group=group, user=request.user).exists():
                            question.group = group
                        else:
                            messages.error(request, 'このグループのメンバーではありません。')
                            return render(request, 'questions/create.html', {'form': form})
                    except StudyGroup.DoesNotExist:
                        question.visibility = 'public'
                else:
                    question.visibility = 'public'

            question.save()

            # メディアファイル保存
            self._save_media(request, question)

            # 下書きを削除
            QuestionDraft.objects.filter(
                user=request.user, question__isnull=True
            ).delete()

            # Gemini AI回答を非同期で生成
            generate_ai_answer.delay(question.pk)

            messages.success(request, '質問を投稿しました。AIが回答を生成中です。')
            return redirect('questions:detail', pk=question.pk)

        return render(request, 'questions/create.html', {'form': form})

    def _save_media(self, request, question):
        """メディアファイルを保存"""
        files = request.FILES.getlist('files')
        total_size = sum(f.size for f in files)
        if total_size > MAX_TOTAL_MEDIA_SIZE:
            messages.warning(request, 'ファイルの合計サイズが100MBを超えています。')
            return
        for f in files:
            QuestionMedia.objects.create(
                question=question,
                file=f,
                file_size=f.size,
                original_name=f.name,
            )


class MyQuestionListView(LoginRequiredMixin, View):
    """自分の投稿一覧画面"""

    def get(self, request):
        questions = Question.objects.filter(
            user=request.user
        ).select_related('subject').order_by('-created_at')
        return render(request, 'questions/my_list.html', {
            'questions': questions,
        })


class QuestionEditView(LoginRequiredMixin, View):
    """質問編集画面"""

    def get(self, request, pk):
        question = get_object_or_404(Question, pk=pk, user=request.user)
        form = QuestionForm(instance=question)
        media_files = question.media_files.filter(is_deleted=False)
        answers = question.answers.filter(is_deleted=False).select_related('user')
        return render(request, 'questions/edit.html', {
            'form': form, 'question': question,
            'media_files': media_files, 'answers': answers,
        })

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk, user=request.user)
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()

            # 削除対象メディア
            delete_ids = request.POST.getlist('delete_media')
            if delete_ids:
                for media in QuestionMedia.objects.filter(
                    pk__in=delete_ids, question=question
                ):
                    media.soft_delete(user=request.user, description='質問メディアを削除')

            # 新規メディア追加
            files = request.FILES.getlist('files')
            existing_size = question.total_media_size
            new_size = sum(f.size for f in files)
            if existing_size + new_size > MAX_TOTAL_MEDIA_SIZE:
                messages.warning(request, 'ファイルの合計サイズが100MBを超えています。')
            else:
                for f in files:
                    QuestionMedia.objects.create(
                        question=question, file=f,
                        file_size=f.size, original_name=f.name,
                    )

            messages.success(request, '質問を更新しました。')
            return redirect('questions:detail', pk=question.pk)

        media_files = question.media_files.filter(is_deleted=False)
        answers = question.answers.filter(is_deleted=False).select_related('user')
        return render(request, 'questions/edit.html', {
            'form': form, 'question': question,
            'media_files': media_files, 'answers': answers,
        })


class QuestionDeleteView(LoginRequiredMixin, View):
    """質問削除（論理削除）"""

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk, user=request.user)
        question.soft_delete(user=request.user, description=f'質問「{question.title}」を削除')
        messages.success(request, '質問を削除しました。')
        return redirect('questions:my_list')


class QuestionToggleResolveView(LoginRequiredMixin, View):
    """質問の解決/未解決を切り替え"""

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk, user=request.user)
        question.is_resolved = not question.is_resolved
        question.save(update_fields=['is_resolved'])
        status = '解決済み' if question.is_resolved else '未解決'
        messages.success(request, f'質問を「{status}」に変更しました。')

        # htmxリクエストならバッジだけ返す
        if getattr(request, 'htmx', False):
            if question.is_resolved:
                badge = '<span class="badge bg-success">解決済み</span>'
            else:
                badge = '<span class="badge bg-warning text-dark">未解決</span>'
            return HttpResponse(badge)

        next_url = request.POST.get('next', '')
        if next_url:
            return redirect(next_url)
        return redirect('questions:my_list')


class AnswerDeleteView(LoginRequiredMixin, View):
    """回答削除（質問者が他者の回答を削除）"""

    def post(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        question = answer.question
        # 質問者のみ削除可能
        if question.user != request.user:
            messages.error(request, '回答を削除する権限がありません。')
            return redirect('questions:detail', pk=question.pk)

        answer.soft_delete(
            user=request.user,
            description=f'質問「{question.title}」の回答 (by {answer.user.username}) を削除'
        )
        messages.success(request, '回答を削除しました。')
        return redirect('questions:edit', pk=question.pk)


class QuestionListView(LoginRequiredMixin, View):
    """質問一覧・検索画面"""

    def get(self, request):
        # 公開質問 + 自分が所属するグループの質問
        from groups.models import GroupMembership
        user_group_ids = list(
            GroupMembership.objects.filter(user=request.user)
            .values_list('group_id', flat=True)
        )

        questions = Question.objects.select_related('user', 'subject', 'group').filter(
            Q(visibility='public') |
            Q(visibility='group', group_id__in=user_group_ids) |
            Q(user=request.user)
        )

        # 絞り込み
        subject_id = request.GET.get('subject')
        username = request.GET.get('username', '').strip()
        unresolved = request.GET.get('unresolved')

        if subject_id:
            questions = questions.filter(subject_id=subject_id)
        if username:
            questions = questions.filter(user__username__icontains=username)
        if unresolved:
            questions = questions.filter(is_resolved=False)

        # ソート
        sort = request.GET.get('sort', 'updated')
        if sort == 'name':
            questions = questions.order_by('title')
        else:
            questions = questions.order_by('-updated_at')

        # ページネーション
        from django.core.paginator import Paginator
        paginator = Paginator(questions, 20)
        page = request.GET.get('page', 1)
        questions_page = paginator.get_page(page)

        subjects = Subject.objects.filter(is_deleted=False)

        context = {
            'questions': questions_page,
            'subjects': subjects,
            'current_subject': subject_id,
            'current_username': username,
            'current_unresolved': unresolved,
            'current_sort': sort,
        }

        # htmxリクエストの場合は部分テンプレートを返す
        if request.htmx:
            return render(request, 'questions/partials/question_list.html', context)

        return render(request, 'questions/list.html', context)


class QuestionDetailView(LoginRequiredMixin, View):
    """質問表示画面"""

    def get(self, request, pk):
        question = get_object_or_404(
            Question.objects.select_related('user', 'subject', 'group'), pk=pk
        )

        # グループ質問の場合、メンバーチェック
        if question.visibility == 'group' and question.group:
            from groups.models import GroupMembership
            if not GroupMembership.objects.filter(
                group=question.group, user=request.user
            ).exists() and question.user != request.user:
                messages.error(request, 'この質問は閲覧権限がありません。')
                return redirect('questions:list')

        media_files = question.media_files.filter(is_deleted=False)

        # 回答一覧（リアクションスコア順にソート）
        answers = question.answers.filter(is_deleted=False).select_related('user')
        answers = answers.annotate(
            positive_count=Count(
                'reactions',
                filter=Q(reactions__emoji_type__in=['thumbs_up', 'heart', 'celebration', 'idea'])
            ),
            negative_count=Count(
                'reactions',
                filter=Q(reactions__emoji_type='thumbs_down')
            ),
        ).order_by('-positive_count', 'negative_count', '-created_at')

        # 現在のユーザのリアクション状態を取得
        user_reactions = {}
        if request.user.is_authenticated:
            for reaction in Reaction.objects.filter(
                answer__question=question, user=request.user
            ):
                key = f'{reaction.answer_id}_{reaction.emoji_type}'
                user_reactions[key] = True

        # 質問本文のHTML変換
        rendered_body = render_body(question.body, question.body_format)

        # サンドボックストークン生成
        from content.views import generate_token

        # 各回答の本文もHTML変換し、リアクション情報を付与
        for answer in answers:
            if answer.is_ai_generated:
                answer.rendered_body = answer.body  # AI回答は制限なし
            else:
                answer.rendered_body = render_body(answer.body, answer.body_format)
            answer.sandbox_token = generate_token(answer.pk)
            # ユーザのリアクション種別一覧
            answer.user_reactions = [
                r.emoji_type for r in Reaction.objects.filter(
                    answer=answer, user=request.user
                )
            ] if request.user.is_authenticated else []
            # リアクション件数
            reaction_counts = {}
            for r in answer.reactions.values('emoji_type').annotate(cnt=Count('id')):
                reaction_counts[r['emoji_type']] = r['cnt']
            answer.thumbs_up_count = reaction_counts.get('thumbs_up', 0) or ''
            answer.thumbs_down_count = reaction_counts.get('thumbs_down', 0) or ''
            answer.heart_count = reaction_counts.get('heart', 0) or ''
            answer.celebration_count = reaction_counts.get('celebration', 0) or ''
            answer.idea_count = reaction_counts.get('idea', 0) or ''
            # 返信一覧
            answer.reply_list = answer.replies.filter(is_deleted=False).select_related('user')
            # 注釈一覧
            answer.annotation_list = answer.annotations.filter(
                created_by=request.user
            )

        context = {
            'question': question,
            'media_files': media_files,
            'answers': answers,
            'user_reactions': user_reactions,
            'rendered_body': rendered_body,
            'reply_form': ReplyForm(),
            'content_domain': 'content.sirisa.net',
        }
        return render(request, 'questions/detail.html', context)


class AnswerCreateView(LoginRequiredMixin, View):
    """回答画面"""

    def get(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        form = AnswerForm()
        # 既存の下書きを読み込み
        draft = AnswerDraft.objects.filter(
            user=request.user, question=question, answer__isnull=True
        ).order_by('-auto_saved_at').first()
        if draft:
            form = AnswerForm(initial={
                'body': draft.body,
                'body_format': draft.body_format or 'text',
            })
        return render(request, 'questions/answer.html', {
            'form': form, 'question': question,
        })

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.save(commit=False)
            answer.question = question
            answer.user = request.user
            answer.save()

            # メディアファイル保存
            files = request.FILES.getlist('files')
            total_size = sum(f.size for f in files)
            if total_size > MAX_TOTAL_MEDIA_SIZE:
                messages.warning(request, 'ファイルの合計サイズが100MBを超えています。')
            else:
                for f in files:
                    AnswerMedia.objects.create(
                        answer=answer, file=f,
                        file_size=f.size, original_name=f.name,
                    )

            # 下書きを削除
            AnswerDraft.objects.filter(
                user=request.user, question=question, answer__isnull=True
            ).delete()

            messages.success(request, '回答を投稿しました。')
            return redirect('questions:detail', pk=question.pk)

        return render(request, 'questions/answer.html', {
            'form': form, 'question': question,
        })


# ===== API エンドポイント =====

class QuestionDraftAPIView(LoginRequiredMixin, View):
    """質問下書き自動保存API"""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        question_id = data.get('question_id')
        draft, _ = QuestionDraft.objects.update_or_create(
            user=request.user,
            question_id=question_id,
            defaults={
                'title': data.get('title', ''),
                'subject_id': data.get('subject_id'),
                'custom_subject': data.get('custom_subject', ''),
                'body': data.get('body', ''),
                'body_format': data.get('body_format', 'text'),
            }
        )
        return JsonResponse({'status': 'saved', 'saved_at': str(draft.auto_saved_at)})


class AnswerDraftAPIView(LoginRequiredMixin, View):
    """回答下書き自動保存API"""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        question_id = data.get('question_id')
        if not question_id:
            return JsonResponse({'error': 'question_id is required'}, status=400)

        draft, _ = AnswerDraft.objects.update_or_create(
            user=request.user,
            question_id=question_id,
            answer__isnull=True,
            defaults={
                'body': data.get('body', ''),
                'body_format': data.get('body_format', 'text'),
            }
        )
        return JsonResponse({'status': 'saved', 'saved_at': str(draft.auto_saved_at)})


class ReactionToggleAPIView(LoginRequiredMixin, View):
    """リアクション切替API"""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        answer_id = data.get('answer_id')
        emoji_type = data.get('emoji_type')

        if not answer_id or not emoji_type:
            return JsonResponse({'error': 'answer_id and emoji_type required'}, status=400)

        try:
            answer = Answer.objects.get(pk=answer_id, is_deleted=False)
        except Answer.DoesNotExist:
            return JsonResponse({'error': 'Answer not found'}, status=404)

        # トグル：既存なら削除、なければ作成
        reaction, created = Reaction.objects.get_or_create(
            answer=answer, user=request.user, emoji_type=emoji_type,
        )
        if not created:
            reaction.delete()
            active = False
        else:
            active = True

        # 各絵文字のカウントを返す
        counts = {}
        for emoji in Reaction.EmojiType.values:
            counts[emoji] = answer.reactions.filter(emoji_type=emoji).count()

        return JsonResponse({
            'active': active,
            'counts': counts,
        })


class AnswerStatusAPIView(LoginRequiredMixin, View):
    """AI回答ステータス確認API（htmxポーリング用）"""

    def get(self, request, pk):
        try:
            answer = Answer.objects.select_related('user').get(pk=pk)
        except Answer.DoesNotExist:
            return HttpResponse('', status=404)

        if answer.ai_generation_status == 'completed':
            # 完了した場合、回答カードの部分テンプレートを返す
            if answer.is_ai_generated:
                answer.rendered_body = answer.body  # AI回答は制限なし
            else:
                answer.rendered_body = render_body(answer.body, answer.body_format)
            from content.views import generate_token
            answer.sandbox_token = generate_token(answer.pk)
            answer.user_reactions = []
            if request.user.is_authenticated:
                answer.user_reactions = list(
                    answer.reactions.filter(user=request.user).values_list('emoji_type', flat=True)
                )
            # リアクションカウント
            from django.db.models import Count
            reaction_counts = {}
            for r in answer.reactions.values('emoji_type').annotate(cnt=Count('id')):
                reaction_counts[r['emoji_type']] = r['cnt']
            answer.thumbs_up_count = reaction_counts.get('thumbs_up', 0) or ''
            answer.thumbs_down_count = reaction_counts.get('thumbs_down', 0) or ''
            answer.heart_count = reaction_counts.get('heart', 0) or ''
            answer.celebration_count = reaction_counts.get('celebration', 0) or ''
            answer.idea_count = reaction_counts.get('idea', 0) or ''
            return render(request, 'questions/partials/answer_card.html', {
                'answer': answer,
            })
        elif answer.ai_generation_status == 'failed':
            answer.rendered_body = answer.body
            answer.user_reactions = []
            answer.thumbs_up_count = ''
            answer.thumbs_down_count = ''
            answer.heart_count = ''
            answer.celebration_count = ''
            answer.idea_count = ''
            return render(request, 'questions/partials/answer_card.html', {
                'answer': answer,
            })
        else:
            # まだ生成中
            return render(request, 'questions/partials/ai_answer_loading.html', {
                'answer': answer,
            })


class QuestionExportView(LoginRequiredMixin, View):
    """質問エクスポート"""

    def get(self, request, pk):
        question = get_object_or_404(
            Question.objects.select_related('user', 'subject'), pk=pk
        )
        answers = list(question.answers.filter(is_deleted=False).select_related('user'))
        fmt = request.GET.get('format', 'txt')

        exporters = {
            'csv': export_module.export_csv,
            'xlsx': export_module.export_xlsx,
            'pdf': export_module.export_pdf,
            'md': export_module.export_markdown,
            'txt': export_module.export_txt,
        }

        exporter = exporters.get(fmt)
        if not exporter:
            messages.error(request, f'未対応のフォーマットです: {fmt}')
            return redirect('questions:detail', pk=pk)

        return exporter(question, answers)


# ===== 返信機能 =====

class ReplyCreateView(LoginRequiredMixin, View):
    """回答への返信投稿"""

    def post(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk, is_deleted=False)
        form = ReplyForm(request.POST)
        if form.is_valid():
            body = form.cleaned_data['body']

            reply = Reply.objects.create(
                answer=answer,
                user=request.user,
                body=body,
            )

            # @ai メンションの検出
            if '@ai' in body.lower():
                # AI返信をCeleryで非同期生成
                generate_ai_reply.delay(reply.pk)

        return redirect('questions:detail', pk=answer.question.pk)


class ReplyDeleteView(LoginRequiredMixin, View):
    """返信削除"""

    def post(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        question_pk = reply.answer.question.pk
        if reply.user == request.user or reply.answer.question.user == request.user:
            reply.soft_delete(user=request.user, description='返信を削除')
        return redirect('questions:detail', pk=question_pk)


# ===== AI注釈 API =====

class AIAnnotationCreateView(LoginRequiredMixin, View):
    """AI注釈生成API（数式導出・単語説明）"""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        answer_id = data.get('answer_id')
        selected_text = data.get('selected_text', '')
        annotation_type = data.get('type', 'word')  # 'formula' or 'word'
        context_before = data.get('context_before', '')
        context_after = data.get('context_after', '')

        if not answer_id or not selected_text:
            return JsonResponse({'error': 'answer_id and selected_text required'}, status=400)

        try:
            answer = Answer.objects.get(pk=answer_id, is_deleted=False)
        except Answer.DoesNotExist:
            return JsonResponse({'error': 'Answer not found'}, status=404)

        # 既存の注釈をチェック
        existing = AIAnnotation.objects.filter(
            answer=answer,
            selected_text=selected_text,
            annotation_type=annotation_type,
            created_by=request.user,
        ).first()

        if existing:
            return JsonResponse({
                'status': 'exists',
                'annotation_id': existing.pk,
                'explanation': existing.explanation,
            })

        # AI生成
        try:
            from .services.gemini_service import generate_annotation
            explanation = generate_annotation(
                selected_text=selected_text,
                context_before=context_before,
                context_after=context_after,
                annotation_type=annotation_type,
                subject_name=answer.question.display_subject,
                question_title=answer.question.title,
                question_body=answer.question.body or '',
            )
        except Exception as e:
            logger.error(f'AI注釈生成失敗: {e}')
            return JsonResponse({'error': 'AI生成に失敗しました'}, status=500)

        annotation = AIAnnotation.objects.create(
            answer=answer,
            annotation_type=annotation_type,
            selected_text=selected_text,
            context_before=context_before,
            context_after=context_after,
            explanation=explanation,
            created_by=request.user,
        )

        return JsonResponse({
            'status': 'created',
            'annotation_id': annotation.pk,
            'explanation': annotation.explanation,
        })


class AIAnnotationGetView(LoginRequiredMixin, View):
    """既存のAI注釈を取得"""

    def get(self, request, pk):
        annotation = get_object_or_404(AIAnnotation, pk=pk, created_by=request.user)
        return JsonResponse({
            'annotation_id': annotation.pk,
            'selected_text': annotation.selected_text,
            'annotation_type': annotation.annotation_type,
            'explanation': annotation.explanation,
        })


class AnswerAnnotationsView(LoginRequiredMixin, View):
    """回答に対するユーザの全注釈を取得"""

    def get(self, request, pk):
        annotations = AIAnnotation.objects.filter(
            answer_id=pk,
            created_by=request.user,
        ).values('id', 'selected_text', 'annotation_type', 'explanation')
        return JsonResponse({'annotations': list(annotations)})


class AutoSupplementView(LoginRequiredMixin, View):
    """回答投稿時の自動補完API"""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        answer_body = data.get('body', '')
        subject_name = data.get('subject_name', '')

        if not answer_body:
            return JsonResponse({'error': 'body required'}, status=400)

        try:
            from .services.gemini_service import generate_supplements
            supplements = generate_supplements(answer_body, subject_name)
        except Exception as e:
            logger.error(f'自動補完生成失敗: {e}')
            return JsonResponse({'error': 'AI生成に失敗しました'}, status=500)

        return JsonResponse({'supplements': supplements})

