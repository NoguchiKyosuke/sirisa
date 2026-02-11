"""
SIRISA アカウントフォーム
パスワードレス認証（メール認証のみ）
"""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginForm(forms.Form):
    """ログインフォーム（メールアドレスのみ）"""
    email = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com',
            'autofocus': True,
        }),
    )


class RegisterForm(forms.ModelForm):
    """新規登録フォーム（パスワードなし）"""

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ユーザ名',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # 未認証の既存ユーザがいれば削除して再登録を許可
        User.objects.filter(email=email, is_verified=False, is_deleted=False).delete()
        if User.objects.filter(email=email, is_deleted=False).exists():
            raise forms.ValidationError('このメールアドレスは既に登録されています。')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user


class VerifyForm(forms.Form):
    """メール認証コード入力フォーム"""
    code = forms.CharField(
        label='認証コード（6桁）',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autofocus': True,
        }),
    )


class ProfileForm(forms.ModelForm):
    """プロフィール編集フォーム"""

    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
            }),
        }


class EmailChangeForm(forms.Form):
    """メールアドレス変更フォーム"""
    new_email = forms.EmailField(
        label='新しいメールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'new-email@example.com',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_new_email(self):
        email = self.cleaned_data.get('new_email')
        if User.objects.filter(email=email, is_deleted=False).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('このメールアドレスは既に使用されています。')
        return email
