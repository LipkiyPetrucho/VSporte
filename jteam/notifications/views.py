from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Notification
from .services import mark_as_read, mark_all_as_read

NOTIFICATIONS_PER_PAGE = 25


@login_required
def notification_list(request):
    notifications_qs = (
        Notification.objects.filter(recipient=request.user)
        .select_related("actor", "actor__profile", "target_ct")
        .prefetch_related("target")
        .order_by("-created")
    )
    mark_all_as_read(request.user)

    paginator = Paginator(notifications_qs, NOTIFICATIONS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    try:
        notifications = paginator.page(page_number)
    except PageNotAnInteger:
        notifications = paginator.page(1)
    except EmptyPage:
        notifications = paginator.page(paginator.num_pages)

    return render(
        request,
        "notifications/list.html",
        {"notifications": notifications},
    )


@login_required
@require_POST
def mark_read(request):
    notification_id = request.POST.get("notification_id")
    if notification_id:
        notification = get_object_or_404(
            Notification, pk=notification_id, recipient=request.user
        )
        mark_as_read(notification, request.user)
    else:
        mark_all_as_read(request.user)
    return JsonResponse({"ok": True})
