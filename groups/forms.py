"""
SIRISA グループフォーム
"""
from django import forms
from .models import StudyGroup


class StudyGroupForm(forms.ModelForm):
    """グループ作成・編集フォーム"""

    class Meta:
        model = StudyGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'グループ名を入力',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'グループの説明（任意）',
            }),
        }


class InviteCodeForm(forms.Form):
    """招待コード入力フォーム"""
    invite_code = forms.CharField(
        label='招待コード',
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '8桁の招待コードを入力',
            'style': 'text-transform: uppercase; letter-spacing: 2px; font-weight: bold;',
        }),
    )
