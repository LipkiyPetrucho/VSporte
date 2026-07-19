from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import (
    LoginForm,
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    InterestsForm,
    SearchForm,
)
from .interests import INTEREST_CATEGORIES
from .models import Profile, Contact, Friendship
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
)


def user_login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request, username=cd["username"], password=cd["password"]
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Добро пожаловать, {user.username}!")
                    return redirect("dashboard")
                else:
                    messages.error(request, "Аккаунт отключен")
            else:
                messages.error(request, "Неверный логин или пароль")
    else:
        form = LoginForm()
    return render(request, "account/login.html", {"form": form})


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


def register(request):
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object,
            # but don't save it yet.
            new_user = user_form.save(commit=False)
            # set the selected password
            new_user.set_password(user_form.cleaned_data["password"])

            # save the object User
            new_user.save()
            # Создать профиль пользователя
            Profile.objects.create(user=new_user)
            create_action(new_user, "создал(а) учётную запись")
            messages.success(request, f"Аккаунт {new_user.username} успешно создан!")
            return render(request, "account/register_done.html", {"new_user": new_user})
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме")
    else:
        user_form = UserRegistrationForm()
    return render(request, "account/register.html", {"user_form": user_form})


@login_required
def edit(request):
    """Обрабатывает редактирование профиля пользователя."""
    if request.method == "POST":
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=request.user.profile, data=request.POST, files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Профиль успешно обновлён")
            return redirect("user_detail", username=request.user.username)
        messages.error(request, "Ошибка при обновлении профиля")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
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
def user_list(request):
    users = (
        User.objects.filter(is_active=True)
        .exclude(pk=request.user.pk)
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
    user = get_object_or_404(
        User.objects.select_related("profile"), username=username, is_active=True
    )
    is_own_profile = request.user == user
    profile_stats = get_profile_stats(user)
    context = {
        "section": "people",
        "user": user,
        "is_own_profile": is_own_profile,
        "profile_stats": profile_stats,
        "activity_items": get_user_activity(user),
    }
    if not is_own_profile:
        context["friendship"] = get_friendship_status(request.user, user)
    return render(request, "account/user/detail.html", context)


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
