"""
SIRISA 質問・回答フォーム
"""
from django import forms
from .models import Question, Answer, QuestionMedia, AnswerMedia, Subject


class QuestionForm(forms.ModelForm):
    """質問投稿・編集フォーム"""

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_deleted=False),
        label='教科',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_subject'}),
    )

    visibility = forms.ChoiceField(
        label='公開範囲',
        choices=[('public', '全体公開'), ('group', 'グループ内')],
        initial='public',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )

    group = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_group'}),
    )

    class Meta:
        model = Question
        fields = ['title', 'subject', 'custom_subject', 'body', 'body_format', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '質問タイトルを入力',
            }),
            'custom_subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '教科名を入力',
                'style': 'display: none;',
                'id': 'id_custom_subject',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': '質問内容を入力してください',
                'id': 'id_body',
            }),
            'body_format': forms.RadioSelect(
                choices=Question.BodyFormat.choices,
                attrs={'class': 'form-check-input'},
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            from groups.models import GroupMembership
            memberships = GroupMembership.objects.filter(
                user=user
            ).select_related('group').filter(group__is_active=True)
            self._user_groups = [(m.group.pk, m.group.name) for m in memberships]
        else:
            self._user_groups = []

    @property
    def user_groups(self):
        return self._user_groups


class AnswerForm(forms.ModelForm):
    """回答フォーム"""

    class Meta:
        model = Answer
        fields = ['body', 'body_format']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': '回答を入力してください',
                'id': 'id_answer_body',
            }),
            'body_format': forms.RadioSelect(
                choices=Answer.BodyFormat.choices,
                attrs={'class': 'form-check-input'},
            ),
        }


class MediaUploadForm(forms.Form):
    """メディアアップロードフォーム"""
    files = forms.FileField(
        label='ファイル',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,audio/*,video/*,.pdf,.doc,.docx,.txt',
        }),
    )


class ReplyForm(forms.Form):
    """返信フォーム"""
    body = forms.CharField(
        label='返信内容',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '返信を入力... @ai でAIに質問できます',
        }),
    )

