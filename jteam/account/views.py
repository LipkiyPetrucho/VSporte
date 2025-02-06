from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import (
    LoginForm,
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    SearchForm,
)
from .models import Profile, Contact
from actions.utils import create_action
from actions.models import Action
from .service import search_users


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
                    return HttpResponse("Authenticated successfully")
                else:
                    return HttpResponse("Disabled account")
            else:
                return HttpResponse("Invalid login")
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
    return render(
        request, "account/dashboard.html", {"section": "dashboard", "actions": actions}
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
            return render(request, "account/register_done.html", {"new_user": new_user})
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
            messages.success(request, "Profile updated ", "successfully")
        else:
            messages.error(request, "Error updating your profile")
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    return render(
        request,
        "account/edit.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


@login_required
def user_list(request):
    users = User.objects.filter(is_active=True)
    return render(
        request,
        "account/user/list.html",
        {"section": "people", "users": users, "form": SearchForm()},
    )


@login_required
def user_detail(request, username):
    user = get_object_or_404(User, username=username, is_active=True)
    return render(
        request, "account/user/detail.html", {"section": "people", "user": user}
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
