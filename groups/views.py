"""
SIRISA グループビュー
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views import View

from .models import StudyGroup, GroupMembership
from .forms import StudyGroupForm, InviteCodeForm


class GroupListView(LoginRequiredMixin, View):
    """自分が所属するグループ一覧"""

    def get(self, request):
        memberships = GroupMembership.objects.filter(
            user=request.user
        ).select_related('group', 'group__owner').order_by('-created_at')
        return render(request, 'groups/list.html', {
            'memberships': memberships,
            'invite_form': InviteCodeForm(),
        })


class GroupCreateView(LoginRequiredMixin, View):
    """グループ作成"""

    def get(self, request):
        return render(request, 'groups/create.html', {
            'form': StudyGroupForm(),
        })

    def post(self, request):
        form = StudyGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.save()
            # オーナーをメンバーとして追加
            GroupMembership.objects.create(
                group=group, user=request.user, role='owner',
            )
            messages.success(request, f'グループ「{group.name}」を作成しました。')
            return redirect('groups:detail', pk=group.pk)
        return render(request, 'groups/create.html', {'form': form})


class GroupDetailView(LoginRequiredMixin, View):
    """グループ詳細"""

    def get(self, request, pk):
        group = get_object_or_404(StudyGroup, pk=pk, is_active=True)
        # メンバーチェック
        membership = GroupMembership.objects.filter(
            group=group, user=request.user
        ).first()
        if not membership:
            messages.error(request, 'このグループのメンバーではありません。')
            return redirect('groups:list')

        members = group.memberships.select_related('user').order_by('role', 'created_at')
        # グループ内の質問一覧
        from questions.models import Question
        questions = Question.objects.filter(
            group=group, is_deleted=False
        ).select_related('user', 'subject').order_by('-created_at')

        return render(request, 'groups/detail.html', {
            'group': group,
            'membership': membership,
            'members': members,
            'questions': questions,
        })


class GroupJoinView(LoginRequiredMixin, View):
    """招待コードでグループに参加"""

    def post(self, request):
        form = InviteCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['invite_code'].upper()
            try:
                group = StudyGroup.objects.get(invite_code=code, is_active=True)
            except StudyGroup.DoesNotExist:
                messages.error(request, '無効な招待コードです。')
                return redirect('groups:list')

            _, created = GroupMembership.objects.get_or_create(
                group=group, user=request.user,
                defaults={'role': 'member'},
            )
            if created:
                messages.success(request, f'グループ「{group.name}」に参加しました。')
            else:
                messages.info(request, 'すでにこのグループに参加しています。')
            return redirect('groups:detail', pk=group.pk)

        messages.error(request, '招待コードを入力してください。')
        return redirect('groups:list')


class GroupLeaveView(LoginRequiredMixin, View):
    """グループ退出"""

    def post(self, request, pk):
        group = get_object_or_404(StudyGroup, pk=pk)
        membership = GroupMembership.objects.filter(
            group=group, user=request.user
        ).first()

        if not membership:
            messages.error(request, 'このグループに参加していません。')
            return redirect('groups:list')

        if membership.role == 'owner':
            # オーナーは退出不可（先に別メンバーにオーナー移譲が必要）
            other_members = group.memberships.exclude(user=request.user).count()
            if other_members > 0:
                messages.error(request, 'オーナーは退出できません。先に他のメンバーにオーナーを移譲してください。')
                return redirect('groups:detail', pk=group.pk)
            # 自分だけの場合はグループを非アクティブ化
            group.is_active = False
            group.save()

        membership.delete()
        messages.success(request, f'グループ「{group.name}」から退出しました。')
        return redirect('groups:list')


class GroupDeleteView(LoginRequiredMixin, View):
    """グループ削除（オーナーのみ）"""

    def post(self, request, pk):
        group = get_object_or_404(StudyGroup, pk=pk, owner=request.user)
        group.is_active = False
        group.save()
        messages.success(request, f'グループ「{group.name}」を削除しました。')
        return redirect('groups:list')


class GroupRegenerateCodeView(LoginRequiredMixin, View):
    """招待コード再生成（オーナーのみ）"""

    def post(self, request, pk):
        group = get_object_or_404(StudyGroup, pk=pk, owner=request.user)
        import uuid
        group.invite_code = uuid.uuid4().hex[:8].upper()
        group.save(update_fields=['invite_code'])
        messages.success(request, '招待コードを再生成しました。')
        return redirect('groups:detail', pk=group.pk)


class GroupRemoveMemberView(LoginRequiredMixin, View):
    """メンバー除外（オーナーのみ）"""

    def post(self, request, pk, user_id):
        group = get_object_or_404(StudyGroup, pk=pk, owner=request.user)
        membership = GroupMembership.objects.filter(
            group=group, user_id=user_id
        ).exclude(user=request.user).first()
        if membership:
            membership.delete()
            messages.success(request, 'メンバーを除外しました。')
        return redirect('groups:detail', pk=group.pk)
