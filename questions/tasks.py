"""
SIRISA Celery非同期タスク
Gemini AI自動回答生成
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
        # Gemini APIを呼び出して回答を生成
        subject_name = question.display_subject
        html_answer = generate_answer(
            question_title=question.title,
            question_body=question.body,
            subject_name=subject_name,
            body_format=question.body_format,
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
