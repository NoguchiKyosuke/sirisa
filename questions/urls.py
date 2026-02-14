"""
SIRISA 質問アプリURL設定
"""
from django.urls import path
from . import views

app_name = 'questions'

urlpatterns = [
    path('', views.QuestionListView.as_view(), name='list'),
    path('new/', views.QuestionCreateView.as_view(), name='create'),
    path('my/', views.MyQuestionListView.as_view(), name='my_list'),
    path('<int:pk>/', views.QuestionDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.QuestionEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='delete'),
    path('<int:pk>/toggle-resolve/', views.QuestionToggleResolveView.as_view(), name='toggle_resolve'),
    path('<int:pk>/answer/', views.AnswerCreateView.as_view(), name='answer'),
    path('<int:pk>/export/', views.QuestionExportView.as_view(), name='export'),
    path('answer/<int:pk>/delete/', views.AnswerDeleteView.as_view(), name='answer_delete'),
    # 返信
    path('answer/<int:pk>/reply/', views.ReplyCreateView.as_view(), name='reply_create'),
    path('reply/<int:pk>/delete/', views.ReplyDeleteView.as_view(), name='reply_delete'),
    path('api/replies/<int:pk>/status/', views.ReplyStatusAPIView.as_view(), name='reply_status'),
    path('api/answers/<int:pk>/replies/', views.AnswerRepliesAPIView.as_view(), name='answer_replies'),
    # API
    path('api/drafts/question/', views.QuestionDraftAPIView.as_view(), name='draft_question'),
    path('api/drafts/answer/', views.AnswerDraftAPIView.as_view(), name='draft_answer'),
    path('api/reactions/', views.ReactionToggleAPIView.as_view(), name='reaction_toggle'),
    path('api/answers/<int:pk>/status/', views.AnswerStatusAPIView.as_view(), name='answer_status'),
    # AI注釈API
    path('api/annotations/', views.AIAnnotationCreateView.as_view(), name='annotation_create'),
    path('api/annotations/<int:pk>/', views.AIAnnotationGetView.as_view(), name='annotation_get'),
    path('api/answers/<int:pk>/annotations/', views.AnswerAnnotationsView.as_view(), name='answer_annotations'),
    path('api/supplements/', views.AutoSupplementView.as_view(), name='auto_supplement'),
]
