"""
SIRISA Celery非同期タスク
Gemini AI自動回答生成・返信生成
"""
import logging
from celery import shared_task
from django.contrib.auth import get_user_model

logger = logging.getLogger('gemini')
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_ai_answer(self, question_id):
    """
    質問に対してGemini AIの回答を非同期で生成する

    Args:
        question_id: 質問のID
    """
    from questions.models import Question, Answer
    from questions.services.gemini_service import generate_answer

    logger.info(f'AI回答生成タスク開始: question_id={question_id}')

    try:
        question = Question.objects.get(pk=question_id)
    except Question.DoesNotExist:
        logger.error(f'質問が見つかりません: question_id={question_id}')
        return

    # Geminiシステムユーザを取得
    try:
        gemini_user = User.objects.get(role='ai_agent')
    except User.DoesNotExist:
        logger.error('Geminiシステムユーザが見つかりません')
        return

    # AI回答レコードを仮作成（pending状態）
    answer, created = Answer.objects.get_or_create(
        question=question,
        user=gemini_user,
        is_ai_generated=True,
        defaults={
            'body': 'AI回答を生成中です...',
            'body_format': 'html',
            'ai_model': 'gemini-2.0-flash',
            'ai_generation_status': 'pending',
        }
    )

    if not created and answer.ai_generation_status == 'completed':
        logger.info(f'AI回答は既に生成済み: question_id={question_id}')
        return

    try:
        # 添付メディアファイルのパスを収集
        media_paths = []
        for media in question.media_files.filter(is_deleted=False):
            if media.media_type in ('image', 'audio', 'video') and media.file:
                try:
                    path = media.file.path
                    ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
                    mime_map = {
                        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                        'png': 'image/png', 'gif': 'image/gif',
                        'webp': 'image/webp', 'svg': 'image/svg+xml',
                        'mp3': 'audio/mpeg', 'wav': 'audio/wav',
                        'ogg': 'audio/ogg', 'm4a': 'audio/mp4',
                        'mp4': 'video/mp4', 'webm': 'video/webm',
                        'mov': 'video/quicktime', 'avi': 'video/x-msvideo',
                    }
                    mime = mime_map.get(ext, 'application/octet-stream')
                    media_paths.append({'path': path, 'mime': mime})
                    logger.info(f'メディア収集: {path} ({mime})')
                except Exception as e:
                    logger.warning(f'メディアパス取得失敗: {media.pk} - {e}')

        # Gemini APIを呼び出して回答を生成
        subject_name = question.display_subject
        html_answer = generate_answer(
            question_title=question.title,
            question_body=question.body,
            subject_name=subject_name,
            body_format=question.body_format,
            media_paths=media_paths if media_paths else None,
        )

        # 回答を更新
        answer.body = html_answer
        answer.ai_generation_status = 'completed'
        answer.save(update_fields=['body', 'ai_generation_status', 'updated_at'])

        logger.info(f'AI回答生成成功: question_id={question_id}')

    except Exception as exc:
        logger.error(f'AI回答生成失敗: question_id={question_id} - {exc}')

        if self.request.retries < self.max_retries:
            logger.info(f'リトライ {self.request.retries + 1}/{self.max_retries}')
            raise self.retry(exc=exc)
        else:
            # 全リトライ失敗
            answer.body = (
                '<div class="alert alert-warning">'
                '<strong>AI回答の生成に失敗しました。</strong><br>'
                '教師からの回答をお待ちください。'
                '</div>'
            )
            answer.ai_generation_status = 'failed'
            answer.save(update_fields=['body', 'ai_generation_status', 'updated_at'])
            logger.error(f'AI回答生成: 全リトライ失敗 question_id={question_id}')


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def generate_ai_reply(self, reply_id):
    """
    @aiメンション付き返信に対してAI返信を非同期生成する

    Args:
        reply_id: 返信のID
    """
    from questions.models import Reply
    from questions.services.gemini_service import generate_reply_text

    logger.info(f'AI返信生成タスク開始: reply_id={reply_id}')

    try:
        original_reply = Reply.objects.select_related(
            'answer', 'answer__question', 'user'
        ).get(pk=reply_id)
    except Reply.DoesNotExist:
        logger.error(f'返信が見つかりません: reply_id={reply_id}')
        return

    # Geminiシステムユーザを取得
    try:
        gemini_user = User.objects.get(role='ai_agent')
    except User.DoesNotExist:
        logger.error('Geminiシステムユーザが見つかりません')
        return

    # AI返信レコード作成
    ai_reply = Reply.objects.create(
        answer=original_reply.answer,
        user=gemini_user,
        body='AI返信を生成中です...',
        is_ai_generated=True,
        ai_model='gemini-2.0-flash',
        ai_generation_status='pending',
    )

    try:
        question = original_reply.answer.question
        answer_body = original_reply.answer.body

        # 返信スレッドのコンテキストを構築
        thread_context = []
        for r in original_reply.answer.replies.filter(
            is_deleted=False, created_at__lte=original_reply.created_at
        ).select_related('user').order_by('created_at')[:10]:
            thread_context.append(f'{r.user.username}: {r.body}')

        reply_text = generate_reply_text(
            question_title=question.title,
            question_body=question.body,
            answer_body=answer_body,
            thread_context='\n'.join(thread_context),
            user_message=original_reply.body,
            subject_name=question.display_subject,
        )

        ai_reply.body = reply_text
        ai_reply.ai_generation_status = 'completed'
        ai_reply.save(update_fields=['body', 'ai_generation_status', 'updated_at'])

        logger.info(f'AI返信生成成功: reply_id={reply_id}')

    except Exception as exc:
        logger.error(f'AI返信生成失敗: reply_id={reply_id} - {exc}')
        ai_reply.body = 'AI返信の生成に失敗しました。'
        ai_reply.ai_generation_status = 'failed'
        ai_reply.save(update_fields=['body', 'ai_generation_status', 'updated_at'])

        if self.request.retries < self.max_retries:
            ai_reply.delete()
            raise self.retry(exc=exc)
