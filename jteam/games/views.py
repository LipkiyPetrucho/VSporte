import json
import logging
import redis
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from actions.utils import create_action
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest
from django.db.models import Case, When, IntegerField, Q
from easy_thumbnails.files import get_thumbnailer
from notifications.models import Notification
from notifications.services import create_notification, notify_game_updated

from account.service import get_friend_users
from .forms import (
    GameCreateForm,
    GameEditForm,
    GameFilterForm,
    game_conditions_changed,
    snapshot_game_conditions,
)
from .models import Game, GameParticipationRequest, GameInvitation, GameTeamAssignment
from .tasks import sync_game_statuses
from .templatetags.game_extras import GAME_STATUS_LABELS

logger = logging.getLogger(__name__)
User = get_user_model()
CHAT_HISTORY_LIMIT = 100

r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    socket_connect_timeout=2,
)


def track_game_view(game_id):
    try:
        total_views = r.incr(f"game:{game_id}:views")
        r.zincrby("game_ranking", 1, game_id)
        return total_views
    except redis.exceptions.RedisError as exc:
        logger.warning("Redis unavailable, skipping game view tracking: %s", exc)
        return 0


def get_top_ranked_game_ids(limit=10):
    try:
        game_ranking = r.zrange("game_ranking", 0, -1, desc=True)[:limit]
        return [int(game_id) for game_id in game_ranking]
    except redis.exceptions.RedisError as exc:
        logger.warning("Redis unavailable, skipping game ranking: %s", exc)
        return []


def validate_date(value):
    if value < timezone.now().date():
        raise ValidationError("Дата не может быть в прошлом.")


def validate_time(value):
    now = timezone.now()
    if value < now.time() or (value == now.time() and now.date() > value.date()):
        raise ValidationError("Время не может быть в прошлом.")


def _game_map_context(extra=None):
    context = {
        "YANDEX_MAPS_API_KEY": settings.YANDEX_MAPS_API_KEY,
        "YANDEX_MAPS_SUGGEST_API_KEY": settings.YANDEX_MAPS_SUGGEST_API_KEY,
    }
    if extra:
        context.update(extra)
    return context


def _player_thumb_url(player, size=(80, 80)):
    photo = getattr(getattr(player, "profile", None), "photo", None)
    if not photo:
        return None
    thumb_opts = {"size": size, "crop": True, "upscale": True}
    return get_thumbnailer(photo).get_thumbnail(thumb_opts).url


def _build_players_payload(game):
    players = []
    for player in game.joined_players.select_related("profile").all():
        players.append({
            "id": player.pk,
            "username": player.username,
            "photo": _player_thumb_url(player),
            "url": reverse("user_detail", args=[player.username]),
        })
    return players


def _serialize_team_roster(game):
    """Roster для JSON / SSR: teams + bench с photo/url у онлайн-игроков."""
    roster = game.team_roster()
    players_by_id = {
        player.pk: player
        for player in game.joined_players.select_related("profile").all()
    }

    def enrich(entry):
        if entry.get("type") != "user":
            return entry
        player = players_by_id.get(entry["user_id"])
        enriched = dict(entry)
        if player is not None:
            enriched["photo"] = _player_thumb_url(player)
            enriched["url"] = reverse("user_detail", args=[player.username])
        else:
            enriched["photo"] = None
            enriched["url"] = None
        return enriched

    return {
        "teams": {
            1: [enrich(e) for e in roster["teams"][1]],
            2: [enrich(e) for e in roster["teams"][2]],
        },
        "bench": [enrich(e) for e in roster["bench"]],
    }


def _parse_request_payload(request):
    """JSON body или form-data / querydict."""
    content_type = (request.content_type or "").split(";")[0].strip().lower()
    if content_type == "application/json":
        try:
            raw = request.body.decode("utf-8") if request.body else "{}"
            data = json.loads(raw or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None
        return data if isinstance(data, dict) else None
    return request.POST


def _participation_status_for_user(game, user):
    if user in game.joined_players.all():
        return "joined"
    if GameInvitation.objects.filter(
        game=game,
        to_user=user,
        status=GameInvitation.PENDING,
    ).exists():
        return "invited"
    if GameParticipationRequest.objects.filter(
        game=game,
        user=user,
        status=GameParticipationRequest.PENDING,
    ).exists():
        return "pending"
    return "none"


def _pending_invitation_for_user(game, user):
    return GameInvitation.objects.filter(
        game=game,
        to_user=user,
        status=GameInvitation.PENDING,
    ).first()


def _invitable_friends(game, organizer):
    joined_ids = set(
        game.joined_players.values_list("pk", flat=True)
    ) | {organizer.pk}
    pending_invitee_ids = set(
        GameInvitation.objects.filter(
            game=game,
            status=GameInvitation.PENDING,
        ).values_list("to_user_id", flat=True)
    )
    exclude_ids = joined_ids | pending_invitee_ids
    return [
        friend
        for friend in get_friend_users(organizer)
        if friend.pk not in exclude_ids
    ]


def _join_response(game, user):
    payload = {
        "status": "ok",
        "players": _build_players_payload(game),
        "joined_count": game.joined_count(),
        "extra_players": game.extra_players,
        "players_count": game.occupied_seats(),
        "max_players": game.max_players,
        "available_seats": game.available_seats(),
        "participation_status": _participation_status_for_user(game, user),
    }
    if game.is_team_game:
        payload["team_roster"] = _serialize_team_roster(game)
    return JsonResponse(payload)


@login_required
def game_create(request):
    if request.method == "POST":
        form = GameCreateForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_game = form.save(commit=False)
            new_game.user = request.user
            
            logger.info("Форма валидна, начинаем создание игры.")
            logger.info("Полученные координаты: lat=%s, lon=%s",
                        form.cleaned_data.get('latitude'),
                        form.cleaned_data.get('longitude'))
            
            try:
                # Округляем время до минут
                start_time = new_game.start_time.replace(second=0, microsecond=0)
                new_game.start_time = start_time
                
                # Проверяем, что время в будущем
                if start_time <= timezone.localtime(timezone.now()):
                    messages.error(request, "Время начала игры должно быть в будущем")
                    logger.warning("Попытка создания игры в прошлом.")
                    return render(request, "games/game/create.html", _game_map_context({"section": "games", "form": form}))
                
                # Сохраняем координаты без дополнительной проверки, так как фронтенд их гарантирует
                new_game.latitude = form.cleaned_data.get('latitude')
                new_game.longitude = form.cleaned_data.get('longitude')
                
                new_game.save()
                
                logger.info("Игра успешно создана: id=%s, координаты: lat=%s, lon=%s",
                            new_game.id, new_game.latitude, new_game.longitude)
                
                create_action(request.user, "создал(а) игру", new_game)
                messages.success(request, "Игра успешно создана")
                return redirect(new_game.get_absolute_url())
            except ValidationError as e:
                messages.error(request, e.message)
                logger.error("Ошибка валидации при создании игры: %s", e.message)
                return render(request, "games/game/create.html", _game_map_context({"section": "games", "form": form}))
        else:
            logger.warning("Форма невалидна: ошибки - %s", form.errors)
            for field_errors in form.errors.values():
                if field_errors:
                    messages.error(request, field_errors[0])
                    break
    else:
        initial = {}
        place = (request.GET.get("place") or "").strip()
        if place:
            initial["place"] = place
        form = GameCreateForm(initial=initial)
    return render(request, "games/game/create.html", _game_map_context({"section": "games", "form": form}))


@login_required
def game_edit(request, id, slug):
    game = get_object_or_404(Game, id=id, slug=slug)
    game.sync_status()

    if request.user != game.user:
        messages.error(request, "У вас нет прав для редактирования этой игры")
        return redirect(game.get_absolute_url())

    if game.status != "open":
        messages.error(request, "Редактировать можно только открытое мероприятие")
        return redirect(game.get_absolute_url())

    if request.method == "POST":
        before = snapshot_game_conditions(game)
        form = GameEditForm(data=request.POST, files=request.FILES, instance=game)
        if form.is_valid():
            try:
                edited_game = form.save(commit=False)
                start_time = edited_game.start_time.replace(second=0, microsecond=0)
                edited_game.start_time = start_time

                if start_time <= timezone.localtime(timezone.now()):
                    messages.error(request, "Время начала игры должно быть в будущем")
                    return render(
                        request,
                        "games/game/create.html",
                        _game_map_context(_edit_form_context(form, edited_game)),
                    )

                edited_game.latitude = form.cleaned_data.get("latitude")
                edited_game.longitude = form.cleaned_data.get("longitude")
                edited_game.save()

                if not edited_game.is_team_game:
                    edited_game.clear_team_assignments()

                if game_conditions_changed(before, edited_game):
                    notify_game_updated(edited_game, request.user)

                create_action(request.user, "изменил(а) игру", edited_game)
                messages.success(request, "Мероприятие обновлено")
                return redirect(edited_game.get_absolute_url())
            except ValidationError as e:
                messages.error(request, e.message)
                return render(
                    request,
                    "games/game/create.html",
                    _game_map_context(_edit_form_context(form, game)),
                )
        else:
            for field_errors in form.errors.values():
                if field_errors:
                    messages.error(request, field_errors[0])
                    break
    else:
        form = GameEditForm(instance=game)

    return render(
        request,
        "games/game/create.html",
        _game_map_context(_edit_form_context(form, game)),
    )


def _edit_form_context(form, game):
    min_players = getattr(form, "min_players", 2)
    return {
        "section": "games",
        "form": form,
        "game": game,
        "is_edit": True,
        "page_title": "Редактировать мероприятие",
        "submit_label": "Сохранить",
        "cancel_url": game.get_absolute_url(),
        "form_error_message": "Не удалось сохранить изменения. Проверьте поля с ошибками.",
        "min_players": min_players,
    }


def game_detail(request, id, slug):
    game = get_object_or_404(Game, id=id, slug=slug)
    game.sync_status()
    total_views = track_game_view(game.id)
    end_time = game.start_time + game.duration
    is_organizer = request.user.is_authenticated and request.user == game.user
    is_joined = (
        request.user.is_authenticated
        and request.user in game.joined_players.all()
    )
    has_pending_request = False
    has_pending_invitation = False
    pending_invitation = None
    pending_participation_requests = []
    invite_friends = []
    pending_invitations = []
    if request.user.is_authenticated:
        has_pending_request = GameParticipationRequest.objects.filter(
            game=game,
            user=request.user,
            status=GameParticipationRequest.PENDING,
        ).exists()
        pending_invitation = _pending_invitation_for_user(game, request.user)
        has_pending_invitation = pending_invitation is not None
        if is_organizer:
            pending_participation_requests = (
                GameParticipationRequest.objects.filter(
                    game=game,
                    status=GameParticipationRequest.PENDING,
                )
                .select_related("user", "user__profile")
                .order_by("created")
            )
            invite_friends = _invitable_friends(game, request.user)
            pending_invitations = (
                GameInvitation.objects.filter(
                    game=game,
                    status=GameInvitation.PENDING,
                )
                .select_related("to_user", "to_user__profile")
                .order_by("created")
            )
    share_url = request.build_absolute_uri(game.get_absolute_url())
    share_text = (
        f"{game.get_sport_display().capitalize()} · {game.place} · "
        f"{timezone.localtime(game.start_time).strftime('%d.%m.%Y %H:%M')}"
    )
    return render(
        request,
        "games/game/detail.html",
        {
            "section": "games",
            "game": game,
            "total_views": total_views,
            "end_time": end_time,
            "total_cost": game.price * game.max_players,
            "available_seats": game.available_seats(),
            "occupied_seats": game.occupied_seats(),
            "max_extra_players": max(0, game.max_players - game.joined_players.count()),
            "is_organizer": is_organizer,
            "is_joined": is_joined,
            "has_pending_request": has_pending_request,
            "has_pending_invitation": has_pending_invitation,
            "pending_invitation": pending_invitation,
            "pending_participation_requests": pending_participation_requests,
            "invite_friends": invite_friends,
            "pending_invitations": pending_invitations,
            "share_url": share_url,
            "share_text": share_text,
            "team_roster": (
                _serialize_team_roster(game) if game.is_team_game else None
            ),
            **_game_map_context(),
        },
    )


def _message_author_photo_url(author):
    photo = getattr(getattr(author, "profile", None), "photo", None)
    if not photo:
        return None
    thumb_opts = {"size": (42, 42), "crop": True, "upscale": True}
    return get_thumbnailer(photo).get_thumbnail(thumb_opts).url


def _serialize_chat_message(message, current_user=None):
    author = message.author
    return {
        "id": message.id,
        "text": message.text,
        "created_at": timezone.localtime(message.created_at).isoformat(),
        "is_own": bool(
            current_user
            and current_user.is_authenticated
            and author.pk == current_user.pk
        ),
        "author": {
            "id": author.pk,
            "username": author.username,
            "photo": _message_author_photo_url(author),
            "url": reverse("user_detail", args=[author.username]),
        },
    }


def _chat_messages_queryset(game):
    return game.messages.select_related("author", "author__profile").order_by(
        "created_at"
    )


def _latest_chat_messages(game, limit=CHAT_HISTORY_LIMIT):
    messages = list(_chat_messages_queryset(game).order_by("-created_at")[:limit])
    messages.reverse()
    return messages


@login_required
def game_chat(request, id, slug):
    """Страница чата игры: история сообщений (realtime — через WebSocket)."""
    game = get_object_or_404(Game, id=id, slug=slug)
    if not game.user_can_access_chat(request.user):
        messages.error(request, "Чат доступен только участникам игры")
        return redirect(game.get_absolute_url())
    chat_messages = _latest_chat_messages(game)
    return render(
        request,
        "games/game/chat.html",
        {
            "section": "games",
            "game": game,
            "chat_messages": chat_messages,
            "messages_url": reverse(
                "games:chat_messages", args=[game.pk, game.slug]
            ),
        },
    )


@login_required
@require_GET
def game_chat_messages(request, id, slug):
    """JSON-история сообщений чата (?after_id= для подгрузки новых)."""
    game = get_object_or_404(Game, id=id, slug=slug)
    if not game.user_can_access_chat(request.user):
        return JsonResponse(
            {"status": "error", "message": "Чат доступен только участникам игры"},
            status=403,
        )

    after_id = request.GET.get("after_id")
    qs = _chat_messages_queryset(game)
    if after_id:
        try:
            after_id = int(after_id)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "Некорректный after_id"}, status=400)
        messages = list(qs.filter(id__gt=after_id)[:CHAT_HISTORY_LIMIT])
    else:
        messages = _latest_chat_messages(game)

    return JsonResponse({
        "status": "ok",
        "messages": [
            _serialize_chat_message(message, request.user)
            for message in messages
        ],
    })


def game_status(request, id):
    """Лёгкий JSON-эндпоинт для опроса статуса игры со страницы деталей."""
    game = get_object_or_404(Game, id=id)
    game.sync_status()
    return JsonResponse({
        "status": game.status,
        "label": GAME_STATUS_LABELS.get(game.status, game.status),
    })


@login_required
def game_list(request):
    """Выводит постраничный список игр с фильтрацией"""
    sync_game_statuses()
    games = Game.objects.select_related("user", "user__profile").prefetch_related(
        "joined_players"
    )
    form = GameFilterForm(request.GET)
    active_tab = request.GET.get("tab", "my_sport")
    if active_tab not in {"calendar", "my_sport", "other"}:
        active_tab = "my_sport"

    open_only = request.GET.get("open_only") in {"1", "true", "yes", "on"}

    user_sports = (
        Game.objects.filter(Q(user=request.user) | Q(joined_players=request.user))
        .values_list("sport", flat=True)
        .distinct()
    )

    if active_tab == "my_sport" and user_sports:
        games = games.filter(sport__in=user_sports)
    elif active_tab == "other" and user_sports:
        games = games.exclude(sport__in=user_sports)

    if open_only:
        games = games.filter(status="open")

    # Активные игры сверху (новые первыми), завершённые — внизу
    games = games.annotate(
        status_priority=Case(
            When(status="open", then=1),
            When(status="started", then=2),
            When(status="finished", then=3),
            default=4,
            output_field=IntegerField(),
        )
    ).order_by("status_priority", "-start_time")
    if form.is_valid():
        sport = form.cleaned_data.get('sport')
        search = form.cleaned_data.get('search')
        
        if sport:
            games = games.filter(sport=sport)
            
        if search:
            games = games.annotate(
                similarity_username=TrigramSimilarity('user__username', search),
                similarity_first_name=TrigramSimilarity('user__first_name', search),
                similarity_last_name=TrigramSimilarity('user__last_name', search)
            ).annotate(
                similarity=Greatest(
                    'similarity_username',
                    'similarity_first_name',
                    'similarity_last_name'
                )
            ).filter(similarity__gt=0.1).order_by("-similarity", "status_priority", "-start_time")

    # Пагинация: по 6 карточек, дальше — кнопка «Ещё»
    paginator = Paginator(games, 6)
    page = request.GET.get("page")
    games_only = request.GET.get("games_only")
    
    try:
        games = paginator.page(page)
    except PageNotAnInteger:
        # Если page_number не целое число, то выдать первую страницу
        games = paginator.page(1)
    except EmptyPage:
        if games_only:
            # Если AJAX-запрос и страница вне диапазона, то вернуть пустую страницу
            return HttpResponse("")
        # Если страница вне диапазона, то вернуть последнюю страницу результатов
        games = paginator.page(paginator.num_pages)
    
    if games_only:
        response = render(
            request,
            "games/game/list_games.html",
            {"section": "games", "games": games},
        )
        response["X-Has-Next"] = "1" if games.has_next() else "0"
        return response

    return render(
        request,
        "games/game/list.html",
        {
            "section": "games",
            "games": games,
            "filter_form": form,
            "active_tab": active_tab,
            "open_only": open_only,
        },
    )


@login_required
@require_POST
def game_join(request):
    """Представление для присоединения, выхода и отмены заявки на участие."""
    game_id = request.POST.get("id")
    action = request.POST.get("action")
    if not game_id or not action:
        return JsonResponse({"status": "error"})

    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return JsonResponse({"status": "error"})

    game.sync_status()

    if game.status != "open":
        return JsonResponse({
            "status": "error",
            "message": "Игра недоступна для изменения участия.",
        })

    if action == "join":
        if request.user in game.joined_players.all():
            return JsonResponse({
                "status": "error",
                "message": "Вы уже участвуете в этой игре.",
            })

        if game.is_full() and request.user != game.user:
            return JsonResponse({
                "status": "error",
                "message": "Максимальное количество игроков достигнуто.",
            })
        if (
            request.user == game.user
            and game.joined_players.count() >= game.max_players
        ):
            return JsonResponse({
                "status": "error",
                "message": "Максимальное количество игроков достигнуто.",
            })

        # Организатор может сразу войти в список участников без заявки.
        if request.user == game.user:
            game.joined_players.add(request.user)
            create_action(request.user, "присоединился(ась) к игре", game)
            return _join_response(game, request.user)

        if GameInvitation.objects.filter(
            game=game,
            to_user=request.user,
            status=GameInvitation.PENDING,
        ).exists():
            return JsonResponse({
                "status": "error",
                "message": "У вас есть приглашение на эту игру.",
            })

        participation_request, created = (
            GameParticipationRequest.objects.get_or_create(
                game=game,
                user=request.user,
                defaults={"status": GameParticipationRequest.PENDING},
            )
        )
        if not created:
            if participation_request.status == GameParticipationRequest.PENDING:
                return JsonResponse({
                    "status": "error",
                    "message": "Заявка уже отправлена.",
                })
            if participation_request.status == GameParticipationRequest.ACCEPTED:
                return JsonResponse({
                    "status": "error",
                    "message": "Вы уже участвуете в этой игре.",
                })
            participation_request.status = GameParticipationRequest.PENDING
            participation_request.save(update_fields=["status"])

        create_notification(
            game.user,
            request.user,
            Notification.TYPE_GAME_PARTICIPATION_REQUEST,
            participation_request,
        )
        return _join_response(game, request.user)

    if action == "cancel_request":
        updated = GameParticipationRequest.objects.filter(
            game=game,
            user=request.user,
            status=GameParticipationRequest.PENDING,
        ).update(status=GameParticipationRequest.CANCELLED)
        if not updated:
            return JsonResponse({
                "status": "error",
                "message": "Активная заявка не найдена.",
            })
        return _join_response(game, request.user)

    if action == "leave":
        if request.user not in game.joined_players.all():
            return JsonResponse({
                "status": "error",
                "message": "Вы не участвуете в этой игре.",
            })
        game.joined_players.remove(request.user)
        game.clear_user_team_assignment(request.user)
        if request.user != game.user:
            GameParticipationRequest.objects.filter(
                game=game,
                user=request.user,
                status=GameParticipationRequest.ACCEPTED,
            ).update(status=GameParticipationRequest.CANCELLED)
        return _join_response(game, request.user)

    if action == "remove_player":
        if request.user != game.user:
            return JsonResponse({
                "status": "error",
                "message": "Только организатор может удалить участника.",
            })
        user_id = request.POST.get("user_id")
        if not user_id:
            return JsonResponse({"status": "error"})
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error"})

        player = game.joined_players.filter(pk=user_id).first()
        if player is None:
            return JsonResponse({
                "status": "error",
                "message": "Участник не найден.",
            })
        if player.pk == game.user_id:
            return JsonResponse({
                "status": "error",
                "message": "Нельзя удалить организатора.",
            })

        game.joined_players.remove(player)
        game.clear_user_team_assignment(player)
        GameParticipationRequest.objects.filter(
            game=game,
            user=player,
            status=GameParticipationRequest.ACCEPTED,
        ).update(status=GameParticipationRequest.CANCELLED)
        GameInvitation.objects.filter(
            game=game,
            to_user=player,
            status=GameInvitation.ACCEPTED,
        ).update(status=GameInvitation.CANCELLED)
        create_notification(
            player,
            request.user,
            Notification.TYPE_GAME_PLAYER_REMOVED,
            game,
        )
        return _join_response(game, request.user)

    return JsonResponse({"status": "error"})


@login_required
@require_POST
def game_participation(request):
    """Принятие, отклонение или отмена заявки на участие в игре."""
    request_id = request.POST.get("id")
    action = request.POST.get("action")
    if not request_id or not action:
        return JsonResponse({"status": "error"})

    participation_request = get_object_or_404(
        GameParticipationRequest.objects.select_related("game", "user"),
        id=request_id,
    )
    game = participation_request.game
    game.sync_status()

    if game.status != "open":
        return JsonResponse({
            "status": "error",
            "message": "Игра недоступна для изменения участия.",
        })

    if action == "accept":
        if request.user != game.user:
            return JsonResponse({"status": "error"})
        if participation_request.status != GameParticipationRequest.PENDING:
            return JsonResponse({
                "status": "error",
                "message": "Заявка уже обработана.",
            })
        if game.is_full():
            return JsonResponse({
                "status": "error",
                "message": "Максимальное количество игроков достигнуто.",
            })

        participation_request.status = GameParticipationRequest.ACCEPTED
        participation_request.save(update_fields=["status"])
        game.joined_players.add(participation_request.user)
        create_action(
            participation_request.user,
            "присоединился(ась) к игре",
            game,
        )
        create_notification(
            participation_request.user,
            request.user,
            Notification.TYPE_GAME_PARTICIPATION_ACCEPTED,
            participation_request,
        )
        return _join_response(game, request.user)

    if action == "reject":
        if request.user != game.user:
            return JsonResponse({"status": "error"})
        if participation_request.status != GameParticipationRequest.PENDING:
            return JsonResponse({
                "status": "error",
                "message": "Заявка уже обработана.",
            })

        participation_request.status = GameParticipationRequest.REJECTED
        participation_request.save(update_fields=["status"])
        game.clear_user_team_assignment(participation_request.user)
        create_notification(
            participation_request.user,
            request.user,
            Notification.TYPE_GAME_PARTICIPATION_REJECTED,
            participation_request,
        )
        return JsonResponse({"status": "ok"})

    if action == "cancel":
        if request.user != participation_request.user:
            return JsonResponse({"status": "error"})
        if participation_request.status != GameParticipationRequest.PENDING:
            return JsonResponse({
                "status": "error",
                "message": "Заявка уже обработана.",
            })

        participation_request.status = GameParticipationRequest.CANCELLED
        participation_request.save(update_fields=["status"])
        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})


@login_required
@require_POST
def game_invite(request):
    """Создание, принятие, отклонение или отмена приглашения на игру."""
    action = request.POST.get("action")
    if not action:
        return JsonResponse({"status": "error"})

    if action == "invite":
        game_id = request.POST.get("game_id")
        to_user_id = request.POST.get("to_user_id")
        if not game_id or not to_user_id:
            return JsonResponse({"status": "error"})

        game = get_object_or_404(Game, id=game_id)
        game.sync_status()
        if request.user != game.user:
            return JsonResponse({"status": "error"})
        if game.status != "open":
            return JsonResponse({
                "status": "error",
                "message": "Игра недоступна для приглашений.",
            })
        if game.is_full():
            return JsonResponse({
                "status": "error",
                "message": "Максимальное количество игроков достигнуто.",
            })

        to_user = get_object_or_404(User, id=to_user_id)
        if to_user == request.user:
            return JsonResponse({"status": "error"})
        if to_user in game.joined_players.all():
            return JsonResponse({
                "status": "error",
                "message": "Игрок уже участвует в игре.",
            })

        friend_ids = set(
            get_friend_users(request.user).values_list("pk", flat=True)
        )
        if to_user.pk not in friend_ids:
            return JsonResponse({
                "status": "error",
                "message": "Можно приглашать только друзей.",
            })

        invitation, created = GameInvitation.objects.get_or_create(
            game=game,
            to_user=to_user,
            defaults={
                "from_user": request.user,
                "status": GameInvitation.PENDING,
            },
        )
        if not created:
            if invitation.status == GameInvitation.PENDING:
                return JsonResponse({
                    "status": "error",
                    "message": "Приглашение уже отправлено.",
                })
            if invitation.status == GameInvitation.ACCEPTED:
                return JsonResponse({
                    "status": "error",
                    "message": "Игрок уже участвует в игре.",
                })
            invitation.from_user = request.user
            invitation.status = GameInvitation.PENDING
            invitation.save(update_fields=["from_user", "status"])

        create_notification(
            to_user,
            request.user,
            Notification.TYPE_GAME_INVITATION,
            invitation,
        )
        return JsonResponse({
            "status": "ok",
            "invitation_id": invitation.id,
        })

    invitation_id = request.POST.get("id")
    if not invitation_id:
        return JsonResponse({"status": "error"})

    invitation = get_object_or_404(
        GameInvitation.objects.select_related("game", "to_user", "from_user"),
        id=invitation_id,
    )
    game = invitation.game
    game.sync_status()

    if game.status != "open":
        return JsonResponse({
            "status": "error",
            "message": "Игра недоступна для изменения участия.",
        })

    if action == "accept":
        if request.user != invitation.to_user:
            return JsonResponse({"status": "error"})
        if invitation.status != GameInvitation.PENDING:
            return JsonResponse({
                "status": "error",
                "message": "Приглашение уже обработано.",
            })
        if request.user in game.joined_players.all():
            return JsonResponse({
                "status": "error",
                "message": "Вы уже участвуете в этой игре.",
            })
        if game.is_full():
            return JsonResponse({
                "status": "error",
                "message": "Максимальное количество игроков достигнуто.",
            })

        invitation.status = GameInvitation.ACCEPTED
        invitation.save(update_fields=["status"])
        game.joined_players.add(request.user)
        GameParticipationRequest.objects.filter(
            game=game,
            user=request.user,
            status=GameParticipationRequest.PENDING,
        ).update(status=GameParticipationRequest.CANCELLED)
        create_action(request.user, "присоединился(ась) к игре", game)
        return _join_response(game, request.user)

    if action == "decline":
        if request.user != invitation.to_user:
            return JsonResponse({"status": "error"})
        if invitation.status != GameInvitation.PENDING:
            return JsonResponse({
                "status": "error",
                "message": "Приглашение уже обработано.",
            })

        invitation.status = GameInvitation.DECLINED
        invitation.save(update_fields=["status"])
        return JsonResponse({
            "status": "ok",
            "participation_status": _participation_status_for_user(
                game, request.user
            ),
        })

    if action == "cancel":
        if request.user != invitation.from_user:
            return JsonResponse({"status": "error"})
        if invitation.status != GameInvitation.PENDING:
            return JsonResponse({
                "status": "error",
                "message": "Приглашение уже обработано.",
            })

        invitation.status = GameInvitation.CANCELLED
        invitation.save(update_fields=["status"])
        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "error"})


@login_required
@require_POST
def game_organizer_settings(request, id, slug):
    """Быстрые настройки организатора на странице игры."""
    game = get_object_or_404(Game, id=id, slug=slug)
    game.sync_status()

    if request.user != game.user:
        return JsonResponse({"status": "error", "message": "Нет прав"}, status=403)

    if game.status != "open":
        return JsonResponse({
            "status": "error",
            "message": "Настройки доступны только для открытого мероприятия.",
        })

    before = snapshot_game_conditions(game)

    try:
        extra_players = int(request.POST.get("extra_players", game.extra_players))
    except (TypeError, ValueError):
        return JsonResponse({
            "status": "error",
            "message": "Некорректное число доп. участников.",
        })

    joined = game.joined_players.count()
    max_extra = max(0, game.max_players - joined)
    if extra_players < 0 or extra_players > max_extra:
        return JsonResponse({
            "status": "error",
            "message": f"Доп. участников можно указать от 0 до {max_extra}.",
        })

    price_raw = request.POST.get("price")
    if price_raw is not None and price_raw != "":
        try:
            price = Decimal(str(price_raw).replace(",", ".")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if price < 0:
                raise InvalidOperation
            game.price = price
        except (InvalidOperation, ValueError):
            return JsonResponse({
                "status": "error",
                "message": "Некорректная стоимость участия.",
            })

    place_reserved = request.POST.get("place_reserved")
    if place_reserved is not None:
        game.place_reserved = place_reserved in ("1", "true", "on", "True")

    game.extra_players = extra_players
    update_fields = ["extra_players", "updated_at"]
    if price_raw is not None and price_raw != "":
        update_fields.append("price")
    if place_reserved is not None:
        update_fields.append("place_reserved")
    game.save(update_fields=update_fields)
    game.trim_offline_team_assignments(extra_players)

    if game_conditions_changed(before, game):
        notify_game_updated(game, request.user)

    payload = {
        "status": "ok",
        "extra_players": game.extra_players,
        "joined_count": game.joined_count(),
        "players_count": game.occupied_seats(),
        "available_seats": game.available_seats(),
        "price": float(game.price),
        "total_cost": float(game.price * game.max_players),
        "place_reserved": game.place_reserved,
        "max_players": game.max_players,
    }
    if game.is_team_game:
        payload["team_roster"] = _serialize_team_roster(game)
    return JsonResponse(payload)


@login_required
@require_POST
def game_teams(request, id, slug):
    """Назначение участника в команду A/B или возврат на скамейку."""
    game = get_object_or_404(Game, id=id, slug=slug)
    game.sync_status()

    if request.user != game.user:
        return JsonResponse({"status": "error", "message": "Нет прав"}, status=403)

    if game.status != "open":
        return JsonResponse({
            "status": "error",
            "message": "Составы можно менять только у открытой игры.",
        })

    if not game.is_team_game:
        return JsonResponse({
            "status": "error",
            "message": "Игра не является командной.",
        })

    data = _parse_request_payload(request)
    if data is None:
        return JsonResponse({
            "status": "error",
            "message": "Некорректный JSON.",
        }, status=400)

    has_user = "user_id" in data and data.get("user_id") is not None
    has_offline = "offline_slot" in data and data.get("offline_slot") is not None
    if has_user == has_offline:
        return JsonResponse({
            "status": "error",
            "message": "Укажите ровно одно из: user_id или offline_slot.",
        })

    if "team" not in data:
        return JsonResponse({
            "status": "error",
            "message": "Поле team обязательно (1, 2 или null).",
        })

    team_raw = data.get("team")
    if team_raw is None or team_raw == "":
        team = None
    else:
        try:
            team = int(team_raw)
        except (TypeError, ValueError):
            return JsonResponse({
                "status": "error",
                "message": "Команда должна быть 1, 2 или null.",
            })
        if team not in (GameTeamAssignment.TEAM_A, GameTeamAssignment.TEAM_B):
            return JsonResponse({
                "status": "error",
                "message": "Команда должна быть 1, 2 или null.",
            })

    user_id = None
    offline_slot = None

    if has_user:
        try:
            user_id = int(data.get("user_id"))
        except (TypeError, ValueError):
            return JsonResponse({
                "status": "error",
                "message": "Некорректный user_id.",
            })
        if not game.joined_players.filter(pk=user_id).exists():
            return JsonResponse({
                "status": "error",
                "message": "Игрок не в составе игры.",
            })
    else:
        try:
            offline_slot = int(data.get("offline_slot"))
        except (TypeError, ValueError):
            return JsonResponse({
                "status": "error",
                "message": "Некорректный offline_slot.",
            })
        if offline_slot < 0 or offline_slot >= game.extra_players:
            return JsonResponse({
                "status": "error",
                "message": "Офлайн-слот вне диапазона extra_players.",
            })

    if team is None:
        if user_id is not None:
            game.clear_user_team_assignment(user_id)
        else:
            game.team_assignments.filter(offline_slot=offline_slot).delete()
    else:
        if user_id is not None:
            assignment = game.team_assignments.filter(user_id=user_id).first()
            if assignment is None:
                assignment = GameTeamAssignment(
                    game=game,
                    user_id=user_id,
                    team=team,
                )
            else:
                assignment.team = team
        else:
            assignment = game.team_assignments.filter(
                offline_slot=offline_slot
            ).first()
            if assignment is None:
                assignment = GameTeamAssignment(
                    game=game,
                    offline_slot=offline_slot,
                    team=team,
                )
            else:
                assignment.team = team

        try:
            assignment.full_clean()
            assignment.save()
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                message = "; ".join(
                    err for errors in exc.message_dict.values() for err in errors
                )
            else:
                message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return JsonResponse({"status": "error", "message": message})

    return JsonResponse({
        "status": "ok",
        "team_roster": _serialize_team_roster(game),
    })


@login_required
def game_ranking(request):
    game_ranking_ids = get_top_ranked_game_ids()
    most_viewed = list(Game.objects.filter(id__in=game_ranking_ids))
    most_viewed.sort(key=lambda x: game_ranking_ids.index(x.id))
    return render(
        request,
        "games/game/ranking.html",
        {"section": "games", "most_viewed": most_viewed},
    )


@login_required
@require_POST
def game_delete(request, id):
    """Представление для удаления игры"""
    game = get_object_or_404(Game, id=id)
    # Проверяем, является ли текущий пользователь создателем игры
    if game.user == request.user:
        game.delete()
        messages.success(request, "Игра успешно удалена")
        return redirect('games:list')
    else:
        messages.error(request, "У вас нет прав для удаления этой игры")
        return redirect(game.get_absolute_url())
