"""
SIRISA メインURL設定
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('questions/', include('questions.urls', namespace='questions')),
    path('groups/', include('groups.urls', namespace='groups')),
    path('pages/', include('pages.urls', namespace='pages')),
    path('content/', include('content.urls', namespace='content')),
    path('', include('questions.urls_home')),
]

# 開発環境でメディアファイルを配信
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
