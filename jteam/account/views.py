from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
import json
from .forms import (
    EmailLoginForm,
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    InterestsForm,
    SearchForm,
    PreferencesPasswordChangeForm,
    PhoneVerificationForm,
)
from .interests import INTEREST_CATEGORIES
from .location_service import (
    delete_recent_location,
    get_current_location,
    set_living_location,
)
from .models import Profile, Contact, Friendship, PhoneVerification
from .phone_service import (
    PhoneValidationError,
    create_and_send_code,
    verify_code,
)
from actions.utils import create_action, get_user_activity
from actions.models import Action
from games.models import Game
from notifications.models import Notification
from notifications.services import create_notification
from django.utils import timezone
from django.db.models import Q
from .service import (
    search_users,
    apply_played_filter,
    get_friendship_status,
    get_profile_stats,
    get_incoming_friend_requests,
    get_outgoing_friend_requests,
    ensure_profile,
    is_blocked,
    block_user,
    unblock_user,
    get_blocked_users,
    get_blocked_user_ids,
)


PENDING_PHONE_CHANGE_SESSION_KEY = "pending_phone_change"


def user_login(request):
    """Вход по email/логину и паролю."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    email_form = EmailLoginForm()
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        email_form = EmailLoginForm(request.POST)
        if email_form.is_valid():
            cd = email_form.cleaned_data
            user = authenticate(
                request, username=cd["login"], password=cd["password"]
            )
            if user is not None and user.is_active:
                login(request, user)
                messages.success(request, f"Добро пожаловать, {user.username}!")
                return redirect(next_url or "dashboard")
            messages.error(request, "Неверный логин/email или пароль")

    return render(
        request,
        "registration/login.html",
        {
            "email_form": email_form,
            "next": next_url,
        },
    )


@login_required
def dashboard(request):
    # По умолчанию показать все действия
    actions = Action.objects.exclude(user=request.user)
    following_ids = request.user.following.values_list("id", flat=True)
    if following_ids:
        # Если пользователь подписан на других, то извлечь только их действия
        # Здесь user_id__in используется для фильтрации объектов по значению поля user_id.
        # Например, MyModel.objects.filter(user_id__in=[1, 2, 3]) вернет объекты,
        # у которых user_id равен 1, 2 или 3.
        actions = actions.filter(user_id__in=following_ids)

    # В Django, двойное подчеркивание (__) используется для обращения к связанным полям
    # в моделях. В данном случае, user__profile означает, что мы обращаемся к полю profile,
    # связанному с полем user в модели.
    actions = actions.select_related("user", "user__profile")[:10].prefetch_related(
        "target"
    )[:10]
    next_game = (
        Game.objects.filter(start_time__gte=timezone.now(), status="open")
        .order_by("start_time")
        .first()
    )
    return render(
        request,
        "account/dashboard.html",
        {
            "section": "dashboard",
            "actions": actions,
            "next_game": next_game,
        },
    )


@login_required
def preferences(request):
    """Плейсхолдер экрана предпочтений и конфиденциальности."""
    return render(
        request,
        "account/preferences.html",
        {"section": "preferences"},
    )


@login_required
def help_and_support(request):
    """Экран помощи и поддержки."""
    return render(
        request,
        "account/help_and_support.html",
        {
            "section": "help",
            "support_email": "pafos.light@yandex.ru",
            "app_version": "1.16",
        },
    )


@login_required
def privacy_policy(request):
    return render(
        request,
        "account/privacy_policy.html",
        {"section": "preferences"},
    )


@login_required
def terms_of_use(request):
    return render(
        request,
        "account/terms_of_use.html",
        {"section": "preferences"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request):
    if request.method == "GET":
        return render(
            request,
            "account/delete_account.html",
            {"section": "preferences"},
        )

    user = request.user
    logout(request)
    with transaction.atomic():
        user.delete()
    messages.success(request, "Аккаунт удалён")
    return redirect("login")


@login_required
@require_POST
def deactivate_account(request):
    user = request.user
    logout(request)
    user.is_active = False
    user.save(update_fields=["is_active"])
    messages.success(
        request,
        "Аккаунт отключён. Для восстановления свяжитесь с поддержкой.",
    )
    return redirect("login")


class PreferencesPasswordChangeView(PasswordChangeView):
    form_class = PreferencesPasswordChangeForm
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("preferences")

    def form_valid(self, form):
        messages.success(self.request, "Пароль обновлён")
        return super().form_valid(form)


@login_required
def select_interests(request):
    """Экран выбора интересов пользователя."""
    profile = request.user.profile
    if request.method == "POST":
        form = InterestsForm(request.POST)
        if form.is_valid():
            profile.interests = form.cleaned_data.get("interests", [])
            profile.save(update_fields=["interests"])
            messages.success(request, "Интересы сохранены")
            return redirect("preferences")
        messages.error(request, "Не удалось сохранить интересы")
    else:
        form = InterestsForm(initial={"interests": profile.interests or []})

    selected = set(form["interests"].value() or [])
    categories = []
    for title, items in INTEREST_CATEGORIES:
        categories.append(
            {
                "title": title,
                "items": [
                    {
                        "slug": slug,
                        "label": label,
                        "icon": icon,
                        "selected": slug in selected,
                    }
                    for slug, label, icon in items
                ],
            }
        )

    return render(
        request,
        "account/select_interests.html",
        {
            "section": "preferences",
            "form": form,
            "categories": categories,
        },
    )


@login_required
def select_location(request):
    """Экран выбора локации проживания."""
    profile = request.user.profile
    return render(
        request,
        "account/select_location.html",
        {
            "section": "preferences",
            "current_location": get_current_location(profile),
            "recent_locations": profile.recent_locations or [],
        },
    )


@login_required
@require_POST
def save_location(request):
    """Сохраняет выбранную локацию проживания."""
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "error": "invalid_json"}, status=400)

    location = set_living_location(request.user.profile, payload)
    if not location:
        return JsonResponse({"status": "error", "error": "invalid_location"}, status=400)

    city = None
    lat = location.get("latitude")
    lon = location.get("longitude")
    if lat is not None and lon is not None:
        try:
            from location.city_detection import GeocoderUnavailableError, detect_city

            detected = detect_city(lat, lon)
            city = detected.get("city")
            if not city and detected.get("detected_name"):
                city = {"name": detected["detected_name"], "slug": None}
        except GeocoderUnavailableError:
            city = None

    return JsonResponse(
        {
            "status": "ok",
            "location": location,
            "recent_locations": request.user.profile.recent_locations or [],
            "city": city,
            "redirect_url": reverse("preferences"),
        }
    )


@login_required
@require_POST
def delete_recent_location_view(request):
    """Удаляет адрес из списка недавних мест."""
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "error": "invalid_json"}, status=400)

    location_id = payload.get("id")
    if not delete_recent_location(request.user.profile, location_id):
        return JsonResponse({"status": "error", "error": "not_found"}, status=404)

    return JsonResponse(
        {
            "status": "ok",
            "recent_locations": request.user.profile.recent_locations or [],
        }
    )


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            with transaction.atomic():
                new_user = User(
                    username=user_form.cleaned_data["username"],
                    first_name=user_form.cleaned_data.get("first_name") or "",
                    email=user_form.cleaned_data["email"],
                )
                new_user.set_password(user_form.cleaned_data["password"])
                new_user.save()
                profile, _created = Profile.objects.get_or_create(user=new_user)
                phone = user_form.cleaned_data.get("phone")
                if phone:
                    profile.phone = phone
                    profile.phone_verified = False
                    profile.save(update_fields=["phone", "phone_verified"])

            create_action(new_user, "создал(а) учётную запись")
            messages.success(
                request, f"Аккаунт {new_user.username} успешно создан!"
            )
            return render(
                request, "account/register_done.html", {"new_user": new_user}
            )
        messages.error(request, "Пожалуйста, исправьте ошибки в форме")
    else:
        user_form = UserRegistrationForm()
    return render(request, "account/register.html", {"user_form": user_form})


@login_required
def edit(request):
    """Обрабатывает редактирование профиля пользователя."""
    profile = ensure_profile(request.user)
    if request.method == "POST":
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=profile, data=request.POST, files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            old_phone = profile.phone
            new_phone = profile_form.cleaned_data.get("phone")
            profile_form.save()

            if new_phone != old_phone:
                if new_phone is None:
                    profile.phone = None
                    profile.phone_verified = False
                    profile.save(update_fields=["phone", "phone_verified"])
                    messages.success(request, "Профиль обновлён, телефон удалён")
                    return redirect("user_detail", username=request.user.username)
                try:
                    create_and_send_code(
                        new_phone, purpose=PhoneVerification.PURPOSE_CHANGE
                    )
                except PhoneValidationError as exc:
                    messages.error(request, str(exc))
                    return redirect("edit")
                request.session[PENDING_PHONE_CHANGE_SESSION_KEY] = new_phone
                messages.success(
                    request,
                    f"Профиль сохранён. Код подтверждения отправлен на {new_phone}.",
                )
                return redirect("edit_phone_verify")

            messages.success(request, "Профиль успешно обновлён")
            return redirect("user_detail", username=request.user.username)
        messages.error(request, "Ошибка при обновлении профиля")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)
    return render(
        request,
        "account/edit.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "gender_choices": Profile.GENDER_CHOICES,
        },
    )


@login_required
def edit_phone_verify(request):
    pending_phone = request.session.get(PENDING_PHONE_CHANGE_SESSION_KEY)
    if not pending_phone:
        messages.error(request, "Нет ожидающей смены телефона.")
        return redirect("edit")

    form = PhoneVerificationForm()
    if request.method == "POST":
        action = request.POST.get("action", "verify")
        if action == "resend":
            try:
                create_and_send_code(
                    pending_phone, purpose=PhoneVerification.PURPOSE_CHANGE
                )
                messages.success(
                    request, f"Новый код отправлен на {pending_phone}."
                )
            except PhoneValidationError as exc:
                messages.error(request, str(exc))
            return redirect("edit_phone_verify")

        form = PhoneVerificationForm(request.POST)
        if form.is_valid():
            try:
                verify_code(
                    pending_phone,
                    form.cleaned_data["code"],
                    purpose=PhoneVerification.PURPOSE_CHANGE,
                )
            except PhoneValidationError as exc:
                form.add_error("code", str(exc))
                messages.error(request, str(exc))
            else:
                if (
                    Profile.objects.filter(phone=pending_phone)
                    .exclude(user=request.user)
                    .exists()
                ):
                    request.session.pop(PENDING_PHONE_CHANGE_SESSION_KEY, None)
                    messages.error(
                        request, "Этот номер телефона уже используется."
                    )
                    return redirect("edit")

                profile = ensure_profile(request.user)
                profile.phone = pending_phone
                profile.phone_verified = True
                profile.save(update_fields=["phone", "phone_verified"])
                request.session.pop(PENDING_PHONE_CHANGE_SESSION_KEY, None)
                messages.success(request, "Номер телефона подтверждён и сохранён")
                return redirect("user_detail", username=request.user.username)

    return render(
        request,
        "account/edit_phone_verify.html",
        {"form": form, "phone": pending_phone},
    )


@login_required
def user_list(request):
    blocked_ids = get_blocked_user_ids(request.user)
    users = (
        User.objects.filter(is_active=True)
        .exclude(pk=request.user.pk)
        .exclude(pk__in=blocked_ids)
        .select_related("profile")
        .order_by("username")
    )

    played_filter = request.GET.get("played", "all")
    if played_filter not in ("all", "played", "not_played"):
        played_filter = "all"

    requests_filter = request.GET.get("requests", "incoming")
    if requests_filter not in ("incoming", "outgoing"):
        requests_filter = "incoming"

    incoming_requests = get_incoming_friend_requests(request.user)
    outgoing_requests = get_outgoing_friend_requests(request.user)
    request_items = (
        incoming_requests if requests_filter == "incoming" else outgoing_requests
    )

    users = apply_played_filter(users, request.user, played_filter)

    query = None
    form = SearchForm()
    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            if query:
                user_ids = search_users(query).values_list("pk", flat=True)
                users = users.filter(pk__in=user_ids)

    user_items = [
        {
            "user": user,
            "friendship": get_friendship_status(request.user, user),
        }
        for user in users
    ]

    return render(
        request,
        "account/user/list.html",
        {
            "section": "people",
            "user_items": user_items,
            "form": form,
            "query": query,
            "played_filter": played_filter,
            "requests_filter": requests_filter,
            "request_items": request_items,
            "incoming_count": len(incoming_requests),
            "outgoing_count": len(outgoing_requests),
        },
    )


@login_required
def user_detail(request, username):
    user = get_object_or_404(User, username=username, is_active=True)
    ensure_profile(user)
    user = User.objects.select_related("profile").get(pk=user.pk)

    is_own_profile = request.user == user
    viewer_blocked = False
    if not is_own_profile:
        # Не показывать профиль, если этот пользователь заблокировал текущего
        if is_blocked(user, request.user):
            messages.error(request, "Профиль недоступен")
            return redirect("user_list")
        viewer_blocked = is_blocked(request.user, user)

    profile_stats = get_profile_stats(user)
    context = {
        "section": "people",
        "user": user,
        "is_own_profile": is_own_profile,
        "profile_stats": profile_stats,
        "activity_items": get_user_activity(user),
        "is_blocked": viewer_blocked,
    }
    if not is_own_profile:
        context["friendship"] = get_friendship_status(request.user, user)
    return render(request, "account/user/detail.html", context)


@require_POST
@login_required
def user_block(request):
    user_id = request.POST.get("id")
    action = request.POST.get("action")
    if not user_id or action not in ("block", "unblock"):
        return JsonResponse({"status": "error"})

    try:
        other = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({"status": "error"})

    if other == request.user:
        return JsonResponse({"status": "error"})

    if action == "block":
        block_user(request.user, other)
        blocked = True
    else:
        unblock_user(request.user, other)
        blocked = False

    return JsonResponse({"status": "ok", "blocked": blocked})


@login_required
def blocked_users(request):
    users = get_blocked_users(request.user)
    return render(
        request,
        "account/blocked_users.html",
        {
            "section": "preferences",
            "blocked_users": users,
        },
    )


NOTIFICATION_SETTING_OPTIONS = (
    ("notify_game_reminders", "Напоминания об играх"),
    ("notify_chat_messages", "Сообщения в чатах игр"),
    ("notify_activity_updates", "Обновления активности"),
    ("notify_social_updates", "Социальные обновления"),
)


@login_required
def notification_settings(request):
    profile = ensure_profile(request.user)
    settings_list = [
        {
            "key": key,
            "label": label,
            "enabled": getattr(profile, key, True),
        }
        for key, label in NOTIFICATION_SETTING_OPTIONS
    ]
    return render(
        request,
        "account/notification_settings.html",
        {
            "section": "preferences",
            "notification_settings": settings_list,
        },
    )


@require_POST
@login_required
def update_notification_setting(request):
    profile = ensure_profile(request.user)
    key = request.POST.get("key")
    allowed = {field for field, _label in NOTIFICATION_SETTING_OPTIONS}
    if key not in allowed:
        return JsonResponse({"status": "error", "error": "invalid_key"}, status=400)

    raw_value = request.POST.get("enabled", "").lower()
    if raw_value in ("1", "true", "on", "yes"):
        enabled = True
    elif raw_value in ("0", "false", "off", "no"):
        enabled = False
    else:
        return JsonResponse({"status": "error", "error": "invalid_value"}, status=400)

    setattr(profile, key, enabled)
    profile.save(update_fields=[key])
    return JsonResponse({"status": "ok", "key": key, "enabled": enabled})


CONTACT_VISIBILITY_OPTIONS = (
    ("show_email", "Показывать email другим пользователям"),
    ("show_phone", "Показывать телефон другим пользователям"),
    ("show_location", "Показывать локацию другим пользователям"),
    ("show_gender", "Показывать пол другим пользователям"),
)


@login_required
def contact_visibility(request):
    profile = ensure_profile(request.user)
    settings_list = [
        {
            "key": key,
            "label": label,
            "enabled": getattr(profile, key, True),
        }
        for key, label in CONTACT_VISIBILITY_OPTIONS
    ]
    return render(
        request,
        "account/contact_visibility.html",
        {
            "section": "preferences",
            "contact_settings": settings_list,
        },
    )


@require_POST
@login_required
def update_contact_visibility(request):
    profile = ensure_profile(request.user)
    key = request.POST.get("key")
    allowed = {field for field, _label in CONTACT_VISIBILITY_OPTIONS}
    if key not in allowed:
        return JsonResponse({"status": "error", "error": "invalid_key"}, status=400)

    raw_value = request.POST.get("enabled", "").lower()
    if raw_value in ("1", "true", "on", "yes"):
        enabled = True
    elif raw_value in ("0", "false", "off", "no"):
        enabled = False
    else:
        return JsonResponse({"status": "error", "error": "invalid_value"}, status=400)

    setattr(profile, key, enabled)
    profile.save(update_fields=[key])
    return JsonResponse({"status": "ok", "key": key, "enabled": enabled})


@require_POST
@login_required
def user_friendship(request):
    user_id = request.POST.get("id")
    action = request.POST.get("action")
    if not user_id or not action:
        return JsonResponse({"status": "error"})

    try:
        other = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({"status": "error"})

    if other == request.user:
        return JsonResponse({"status": "error"})

    if is_blocked(request.user, other) or is_blocked(other, request.user):
        return JsonResponse({"status": "error", "error": "blocked"})

    if action == "request":
        friendship, created = Friendship.objects.get_or_create(
            from_user=request.user,
            to_user=other,
            defaults={"status": Friendship.PENDING},
        )
        create_action(request.user, "отправил(а) заявку в друзья", other)
        if created:
            create_notification(
                other,
                request.user,
                Notification.TYPE_FRIENDSHIP_REQUEST,
                friendship,
            )
    elif action == "accept":
        friendship = Friendship.objects.filter(
            from_user=other,
            to_user=request.user,
            status=Friendship.PENDING,
        ).first()
        if friendship:
            friendship.status = Friendship.ACCEPTED
            friendship.save(update_fields=["status"])
            create_action(request.user, "принял(а) заявку в друзья", other)
            create_notification(
                other,
                request.user,
                Notification.TYPE_FRIENDSHIP_ACCEPTED,
                friendship,
            )
    elif action == "cancel":
        Friendship.objects.filter(
            from_user=request.user,
            to_user=other,
            status=Friendship.PENDING,
        ).delete()
    elif action == "unfriend":
        Friendship.objects.filter(
            Q(from_user=request.user, to_user=other, status=Friendship.ACCEPTED)
            | Q(from_user=other, to_user=request.user, status=Friendship.ACCEPTED)
        ).delete()
    else:
        return JsonResponse({"status": "error"})

    return JsonResponse(
        {
            "status": "ok",
            "friendship": get_friendship_status(request.user, other),
        }
    )


@require_POST
@login_required
def user_follow(request):
    """Выводит страницу пользователя или 404, если не найден."""
    user_id = request.POST.get("id")
    action = request.POST.get("action")
    if user_id and action:
        try:
            user = User.objects.get(id=user_id)
            if action == "follow":
                Contact.objects.get_or_create(user_from=request.user, user_to=user)
                create_action(request.user, "подписался(ась) на", user)
            else:
                Contact.objects.filter(user_from=request.user, user_to=user).delete()
            return JsonResponse({"status": "ok"})
        except User.DoesNotExist:
            return JsonResponse({"status": "error"})
    return JsonResponse({"status": "error"})


def account_search(request):
    """Поиск игрока по нику, имени и фамилии"""
    form = SearchForm()
    query = None
    results = []
    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            results = search_users(query)
    return render(
        request,
        "account/user/search_results.html",
        {"form": form, "query": query, "results": results},
    )
