from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from easy_thumbnails.files import get_thumbnailer

from account.service import get_friend_users
from actions.utils import create_action
from notifications.models import Notification
from notifications.services import create_notification

from .forms import CommunityCreateForm, CommunityEditForm, CommunityFilterForm
from .models import Community, CommunityInvitation, CommunityJoinRequest

User = get_user_model()


def _member_thumb_url(member, size=(80, 80)):
    photo = getattr(getattr(member, "profile", None), "photo", None)
    if not photo:
        return None
    thumb_opts = {"size": size, "crop": True, "upscale": True}
    return get_thumbnailer(photo).get_thumbnail(thumb_opts).url


def _build_members_payload(community):
    members = []
    for member in community.members.select_related("profile").all():
        members.append(
            {
                "id": member.pk,
                "username": member.username,
                "photo": _member_thumb_url(member),
                "url": reverse("user_detail", args=[member.username]),
                "is_owner": member.pk == community.owner_id,
            }
        )
    return members


def _membership_status_for_user(community, user):
    if not user.is_authenticated:
        return "none"
    if user in community.members.all():
        return "joined"
    if CommunityInvitation.objects.filter(
        community=community,
        to_user=user,
        status=CommunityInvitation.PENDING,
    ).exists():
        return "invited"
    if CommunityJoinRequest.objects.filter(
        community=community,
        user=user,
        status=CommunityJoinRequest.PENDING,
    ).exists():
        return "pending"
    return "none"


def _pending_invitation_for_user(community, user):
    return CommunityInvitation.objects.filter(
        community=community,
        to_user=user,
        status=CommunityInvitation.PENDING,
    ).first()


def _invitable_friends(community, owner):
    member_ids = set(community.members.values_list("pk", flat=True)) | {owner.pk}
    pending_invitee_ids = set(
        CommunityInvitation.objects.filter(
            community=community,
            status=CommunityInvitation.PENDING,
        ).values_list("to_user_id", flat=True)
    )
    exclude_ids = member_ids | pending_invitee_ids
    return [
        friend
        for friend in get_friend_users(owner)
        if friend.pk not in exclude_ids
    ]


def _membership_response(community, user):
    membership_status = _membership_status_for_user(community, user)
    payload = {
        "status": "ok",
        "members": _build_members_payload(community),
        "members_count": community.members.count(),
        "membership_status": membership_status,
    }
    if membership_status == "pending":
        pending = CommunityJoinRequest.objects.filter(
            community=community,
            user=user,
            status=CommunityJoinRequest.PENDING,
        ).only("id").first()
        if pending:
            payload["join_request_id"] = pending.id
    if membership_status == "invited":
        invitation = _pending_invitation_for_user(community, user)
        if invitation:
            payload["invitation_id"] = invitation.id
    return JsonResponse(payload)


def _edit_form_context(form, community):
    return {
        "section": "groups",
        "form": form,
        "community": community,
        "is_edit": True,
        "page_title": "Редактировать группу",
        "submit_label": "Сохранить",
        "cancel_url": community.get_absolute_url(),
        "form_error_message": (
            "Не удалось сохранить изменения. Проверьте поля с ошибками."
        ),
    }


@login_required
def community_list(request):
    """Постраничный список групп с фильтром по виду спорта."""
    communities = Community.objects.select_related(
        "owner", "owner__profile"
    ).prefetch_related("members")
    form = CommunityFilterForm(request.GET)

    if form.is_valid():
        sport = form.cleaned_data.get("sport")
        if sport:
            communities = communities.filter(sport=sport)

    paginator = Paginator(communities, 6)
    page = request.GET.get("page")
    try:
        communities = paginator.page(page)
    except PageNotAnInteger:
        communities = paginator.page(1)
    except EmptyPage:
        communities = paginator.page(paginator.num_pages)

    return render(
        request,
        "groups/community/list.html",
        {
            "section": "groups",
            "communities": communities,
            "filter_form": form,
        },
    )


@login_required
def community_create(request):
    if request.method == "POST":
        form = CommunityCreateForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            community = form.save(commit=False)
            community.owner = request.user
            community.save()
            community.members.add(request.user)
            create_action(request.user, "создал(а) группу", community)
            messages.success(request, "Группа успешно создана")
            return redirect(community.get_absolute_url())
        for field_errors in form.errors.values():
            if field_errors:
                messages.error(request, field_errors[0])
                break
    else:
        form = CommunityCreateForm()

    return render(
        request,
        "groups/community/create.html",
        {
            "section": "groups",
            "form": form,
            "page_title": "Создать группу",
            "submit_label": "Создать",
            "form_error_message": (
                "Не удалось создать группу. Проверьте поля с ошибками."
            ),
        },
    )


def community_detail(request, id, slug):
    community = get_object_or_404(Community, id=id, slug=slug)
    is_owner = (
        request.user.is_authenticated and request.user == community.owner
    )
    is_member = (
        request.user.is_authenticated
        and request.user in community.members.all()
    )
    has_pending_request = False
    has_pending_invitation = False
    pending_invitation = None
    pending_join_request = None
    pending_join_requests = []
    invite_friends = []
    pending_invitations = []

    if request.user.is_authenticated:
        pending_join_request = CommunityJoinRequest.objects.filter(
            community=community,
            user=request.user,
            status=CommunityJoinRequest.PENDING,
        ).first()
        has_pending_request = pending_join_request is not None
        pending_invitation = _pending_invitation_for_user(
            community, request.user
        )
        has_pending_invitation = pending_invitation is not None
        if is_owner:
            pending_join_requests = (
                CommunityJoinRequest.objects.filter(
                    community=community,
                    status=CommunityJoinRequest.PENDING,
                )
                .select_related("user", "user__profile")
                .order_by("created")
            )
            invite_friends = _invitable_friends(community, request.user)
            pending_invitations = (
                CommunityInvitation.objects.filter(
                    community=community,
                    status=CommunityInvitation.PENDING,
                )
                .select_related("to_user", "to_user__profile")
                .order_by("created")
            )

    return render(
        request,
        "groups/community/detail.html",
        {
            "section": "groups",
            "community": community,
            "is_owner": is_owner,
            "is_member": is_member,
            "has_pending_request": has_pending_request,
            "has_pending_invitation": has_pending_invitation,
            "pending_invitation": pending_invitation,
            "pending_join_request": pending_join_request,
            "pending_join_requests": pending_join_requests,
            "invite_friends": invite_friends,
            "pending_invitations": pending_invitations,
            "members_count": community.members.count(),
            "membership_status": _membership_status_for_user(
                community, request.user
            ),
        },
    )


@login_required
def community_edit(request, id, slug):
    community = get_object_or_404(Community, id=id, slug=slug)

    if request.user != community.owner:
        messages.error(request, "У вас нет прав для редактирования этой группы")
        return redirect(community.get_absolute_url())

    if request.method == "POST":
        form = CommunityEditForm(
            data=request.POST, files=request.FILES, instance=community
        )
        if form.is_valid():
            edited = form.save()
            create_action(request.user, "изменил(а) группу", edited)
            messages.success(request, "Группа обновлена")
            return redirect(edited.get_absolute_url())
        for field_errors in form.errors.values():
            if field_errors:
                messages.error(request, field_errors[0])
                break
    else:
        form = CommunityEditForm(instance=community)

    return render(
        request,
        "groups/community/create.html",
        _edit_form_context(form, community),
    )


@login_required
@require_POST
def community_delete(request, id):
    community = get_object_or_404(Community, id=id)
    if community.owner != request.user:
        messages.error(request, "У вас нет прав для удаления этой группы")
        return redirect(community.get_absolute_url())
    community.delete()
    messages.success(request, "Группа успешно удалена")
    return redirect("groups:list")


@login_required
@require_POST
def community_join(request):
    """Заявка на вступление в группу."""
    community_id = request.POST.get("id")
    if not community_id:
        return JsonResponse({"status": "error"})

    try:
        community = Community.objects.get(id=community_id)
    except Community.DoesNotExist:
        return JsonResponse({"status": "error"})

    if request.user in community.members.all():
        return JsonResponse(
            {
                "status": "error",
                "message": "Вы уже состоите в этой группе.",
            }
        )

    if request.user == community.owner:
        community.members.add(request.user)
        create_action(request.user, "вступил(а) в группу", community)
        return _membership_response(community, request.user)

    if CommunityInvitation.objects.filter(
        community=community,
        to_user=request.user,
        status=CommunityInvitation.PENDING,
    ).exists():
        return JsonResponse(
            {
                "status": "error",
                "message": "У вас есть приглашение в эту группу.",
            }
        )

    join_request, created = CommunityJoinRequest.objects.get_or_create(
        community=community,
        user=request.user,
        defaults={"status": CommunityJoinRequest.PENDING},
    )
    if not created:
        if join_request.status == CommunityJoinRequest.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Заявка уже отправлена.",
                }
            )
        if join_request.status == CommunityJoinRequest.ACCEPTED:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Вы уже состоите в этой группе.",
                }
            )
        join_request.status = CommunityJoinRequest.PENDING
        join_request.save(update_fields=["status"])

    create_notification(
        community.owner,
        request.user,
        Notification.TYPE_GROUP_JOIN_REQUEST,
        join_request,
    )
    return _membership_response(community, request.user)


@login_required
@require_POST
def community_leave(request):
    """Выход из группы."""
    community_id = request.POST.get("id")
    if not community_id:
        return JsonResponse({"status": "error"})

    try:
        community = Community.objects.get(id=community_id)
    except Community.DoesNotExist:
        return JsonResponse({"status": "error"})

    if request.user == community.owner:
        return JsonResponse(
            {
                "status": "error",
                "message": "Владелец не может выйти из группы. Удалите группу.",
            }
        )

    if request.user not in community.members.all():
        return JsonResponse(
            {
                "status": "error",
                "message": "Вы не состоите в этой группе.",
            }
        )

    community.members.remove(request.user)
    CommunityJoinRequest.objects.filter(
        community=community,
        user=request.user,
        status=CommunityJoinRequest.ACCEPTED,
    ).update(status=CommunityJoinRequest.CANCELLED)
    return _membership_response(community, request.user)


@login_required
@require_POST
def community_membership(request):
    """Принятие, отклонение, отмена заявки или удаление участника."""
    action = request.POST.get("action")
    if not action:
        return JsonResponse({"status": "error"})

    if action == "remove_member":
        community_id = request.POST.get("community_id") or request.POST.get("id")
        user_id = request.POST.get("user_id")
        if not community_id or not user_id:
            return JsonResponse({"status": "error"})

        community = get_object_or_404(Community, id=community_id)
        if request.user != community.owner:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Только владелец может удалить участника.",
                }
            )

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error"})

        member = community.members.filter(pk=user_id).first()
        if member is None:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Участник не найден.",
                }
            )
        if member.pk == community.owner_id:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Нельзя удалить владельца.",
                }
            )

        community.members.remove(member)
        CommunityJoinRequest.objects.filter(
            community=community,
            user=member,
            status=CommunityJoinRequest.ACCEPTED,
        ).update(status=CommunityJoinRequest.CANCELLED)
        CommunityInvitation.objects.filter(
            community=community,
            to_user=member,
            status=CommunityInvitation.ACCEPTED,
        ).update(status=CommunityInvitation.CANCELLED)
        create_notification(
            member,
            request.user,
            Notification.TYPE_GROUP_MEMBER_REMOVED,
            community,
        )
        return _membership_response(community, request.user)

    request_id = request.POST.get("id")
    if not request_id:
        return JsonResponse({"status": "error"})

    join_request = get_object_or_404(
        CommunityJoinRequest.objects.select_related("community", "user"),
        id=request_id,
    )
    community = join_request.community

    if action == "accept":
        if request.user != community.owner:
            return JsonResponse({"status": "error"})
        if join_request.status != CommunityJoinRequest.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Заявка уже обработана.",
                }
            )

        join_request.status = CommunityJoinRequest.ACCEPTED
        join_request.save(update_fields=["status"])
        community.members.add(join_request.user)
        CommunityInvitation.objects.filter(
            community=community,
            to_user=join_request.user,
            status=CommunityInvitation.PENDING,
        ).update(status=CommunityInvitation.CANCELLED)
        create_action(join_request.user, "вступил(а) в группу", community)
        create_notification(
            join_request.user,
            request.user,
            Notification.TYPE_GROUP_JOIN_ACCEPTED,
            join_request,
        )
        return _membership_response(community, request.user)

    if action == "reject":
        if request.user != community.owner:
            return JsonResponse({"status": "error"})
        if join_request.status != CommunityJoinRequest.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Заявка уже обработана.",
                }
            )

        join_request.status = CommunityJoinRequest.REJECTED
        join_request.save(update_fields=["status"])
        create_notification(
            join_request.user,
            request.user,
            Notification.TYPE_GROUP_JOIN_REJECTED,
            join_request,
        )
        return JsonResponse({"status": "ok"})

    if action == "cancel":
        if request.user != join_request.user:
            return JsonResponse({"status": "error"})
        if join_request.status != CommunityJoinRequest.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Заявка уже обработана.",
                }
            )

        join_request.status = CommunityJoinRequest.CANCELLED
        join_request.save(update_fields=["status"])
        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})


@login_required
@require_POST
def community_invite(request):
    """Создание, принятие, отклонение или отмена приглашения в группу."""
    action = request.POST.get("action")
    if not action:
        return JsonResponse({"status": "error"})

    if action == "invite":
        community_id = request.POST.get("community_id")
        to_user_id = request.POST.get("to_user_id")
        if not community_id or not to_user_id:
            return JsonResponse({"status": "error"})

        community = get_object_or_404(Community, id=community_id)
        if request.user != community.owner:
            return JsonResponse({"status": "error"})

        to_user = get_object_or_404(User, id=to_user_id)
        if to_user == request.user:
            return JsonResponse({"status": "error"})
        if to_user in community.members.all():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Пользователь уже в группе.",
                }
            )

        friend_ids = set(
            get_friend_users(request.user).values_list("pk", flat=True)
        )
        if to_user.pk not in friend_ids:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Можно приглашать только друзей.",
                }
            )

        invitation, created = CommunityInvitation.objects.get_or_create(
            community=community,
            to_user=to_user,
            defaults={
                "from_user": request.user,
                "status": CommunityInvitation.PENDING,
            },
        )
        if not created:
            if invitation.status == CommunityInvitation.PENDING:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Приглашение уже отправлено.",
                    }
                )
            if invitation.status == CommunityInvitation.ACCEPTED:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Пользователь уже в группе.",
                    }
                )
            invitation.from_user = request.user
            invitation.status = CommunityInvitation.PENDING
            invitation.save(update_fields=["from_user", "status"])

        create_notification(
            to_user,
            request.user,
            Notification.TYPE_GROUP_INVITATION,
            invitation,
        )
        return JsonResponse(
            {
                "status": "ok",
                "invitation_id": invitation.id,
            }
        )

    invitation_id = request.POST.get("id")
    if not invitation_id:
        return JsonResponse({"status": "error"})

    invitation = get_object_or_404(
        CommunityInvitation.objects.select_related(
            "community", "to_user", "from_user"
        ),
        id=invitation_id,
    )
    community = invitation.community

    if action == "accept":
        if request.user != invitation.to_user:
            return JsonResponse({"status": "error"})
        if invitation.status != CommunityInvitation.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Приглашение уже обработано.",
                }
            )
        if request.user in community.members.all():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Вы уже состоите в этой группе.",
                }
            )

        invitation.status = CommunityInvitation.ACCEPTED
        invitation.save(update_fields=["status"])
        community.members.add(request.user)
        CommunityJoinRequest.objects.filter(
            community=community,
            user=request.user,
            status=CommunityJoinRequest.PENDING,
        ).update(status=CommunityJoinRequest.CANCELLED)
        create_action(request.user, "вступил(а) в группу", community)
        return _membership_response(community, request.user)

    if action == "decline":
        if request.user != invitation.to_user:
            return JsonResponse({"status": "error"})
        if invitation.status != CommunityInvitation.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Приглашение уже обработано.",
                }
            )

        invitation.status = CommunityInvitation.DECLINED
        invitation.save(update_fields=["status"])
        return JsonResponse(
            {
                "status": "ok",
                "membership_status": _membership_status_for_user(
                    community, request.user
                ),
            }
        )

    if action == "cancel":
        if request.user != invitation.from_user:
            return JsonResponse({"status": "error"})
        if invitation.status != CommunityInvitation.PENDING:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Приглашение уже обработано.",
                }
            )

        invitation.status = CommunityInvitation.CANCELLED
        invitation.save(update_fields=["status"])
        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})
