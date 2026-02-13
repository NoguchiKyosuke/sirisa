"""
SIRISA 静的ページビュー
"""
from django.shortcuts import render
from django.views import View


class HowToUseView(View):
    """使い方ページ"""
    def get(self, request):
        return render(request, 'pages/how_to_use.html')


class FAQView(View):
    """FAQページ"""
    def get(self, request):
        return render(request, 'pages/faq.html')


class ContactView(View):
    """お問い合わせページ"""
    def get(self, request):
        return render(request, 'pages/contact.html')


class TermsView(View):
    """利用規約ページ"""
    def get(self, request):
        return render(request, 'pages/terms.html')


class PrivacyView(View):
    """プライバシーポリシーページ"""
    def get(self, request):
        return render(request, 'pages/privacy.html')
