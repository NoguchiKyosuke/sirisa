from django.contrib import admin
from .models import StudyGroup, GroupMembership


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'invite_code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'owner__username']


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['group', 'user', 'role', 'created_at']
    list_filter = ['role']
