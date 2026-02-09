"""
SIRISA Gmail APIサービス
認証コードメール送信機能
"""
import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_verification_email(user, code):
    """
    認証コードをメールで送信する

    Gmail APIの本格的な設定が完了するまでは
    Django標準のメール送信機能を使用する。
    本番ではGmail API (OAuth2) に切り替え可能。
    """
    subject = '【SIRISA】メール認証コード'
    html_message = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2c3e50;">SIRISA メール認証</h2>
        <p>{user.username} さん、こんにちは。</p>
        <p>以下の認証コードを入力してください。</p>
        <div style="background: #f8f9fa; padding: 20px; text-align: center;
                    border-radius: 8px; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                         color: #2c3e50;">{code}</span>
        </div>
        <p style="color: #6c757d; font-size: 14px;">
            このコードは5分間有効です。<br>
            心当たりのない場合は、このメールを無視してください。
        </p>
        <hr style="border: none; border-top: 1px solid #dee2e6;">
        <p style="color: #adb5bd; font-size: 12px;">SIRISA - 学習補助プラットフォーム</p>
    </div>
    """
    plain_message = (
        f'{user.username} さん、こんにちは。\n\n'
        f'認証コード: {code}\n\n'
        f'このコードは5分間有効です。\n'
        f'心当たりのない場合は、このメールを無視してください。\n\n'
        f'SIRISA - 学習補助プラットフォーム'
    )

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.GMAIL_SENDER_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'認証メール送信成功: {user.email}')
        return True
    except Exception as e:
        logger.error(f'認証メール送信失敗: {user.email} - {e}')
        return False
