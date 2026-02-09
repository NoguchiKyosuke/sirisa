from django.contrib import admin
from .models import Subject, Question, QuestionMedia, Answer, AnswerMedia, Reaction


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_custom', 'order', 'is_deleted')
    ordering = ('order',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'subject', 'body_format', 'is_resolved', 'is_deleted', 'created_at')
    list_filter = ('subject', 'body_format', 'is_resolved', 'is_deleted')
    search_fields = ('title', 'body', 'user__email')
    raw_id_fields = ('user', 'subject')
    date_hierarchy = 'created_at'


@admin.register(QuestionMedia)
class QuestionMediaAdmin(admin.ModelAdmin):
    list_display = ('question', 'media_type', 'original_name', 'created_at')
    list_filter = ('media_type',)
    raw_id_fields = ('question',)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'is_ai_generated', 'ai_generation_status', 'is_deleted', 'created_at')
    list_filter = ('is_ai_generated', 'ai_generation_status', 'is_deleted')
    search_fields = ('body', 'user__email')
    raw_id_fields = ('user', 'question')


@admin.register(AnswerMedia)
class AnswerMediaAdmin(admin.ModelAdmin):
    list_display = ('answer', 'media_type', 'original_name', 'created_at')
    list_filter = ('media_type',)
    raw_id_fields = ('answer',)


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('answer', 'user', 'emoji_type', 'created_at')
    list_filter = ('emoji_type',)
    raw_id_fields = ('answer', 'user')
