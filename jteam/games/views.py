import redis
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from actions.utils import create_action

from .forms import GameCreateForm
from .models import Game


def validate_date(value):
    if value < timezone.now().date():
        raise ValidationError("Дата не может быть в прошлом.")


def validate_time(value):
    now = timezone.now()
    if value < now.time() or (value == now.time() and now.date() > value.date()):
        raise ValidationError("Время не может быть в прошлом.")


@login_required
def game_create(request):
    if request.method == "POST":
        form = GameCreateForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_game = form.save(commit=False)
            new_game.user = request.user
            
            try:
                # Округляем время до минут
                start_time = new_game.start_time.replace(second=0, microsecond=0)
                new_game.start_time = start_time
                
                # Проверяем, что время в будущем
                if start_time <= timezone.localtime(timezone.now()):
                    messages.error(request, "Время начала игры должно быть в будущем")
                    return render(request, "games/game/create.html", {"section": "games", "form": form})
                
                new_game.save()
                create_action(request.user, "создал(а) игру", new_game)
                messages.success(request, "Игра успешно создана")
                return redirect(new_game.get_absolute_url())
            except ValidationError as e:
                messages.error(request, e.message)
                return render(request, "games/game/create.html", {"section": "games", "form": form})
    else:
        form = GameCreateForm()
    return render(request, "games/game/create.html", {"section": "games", "form": form})


def game_detail(request, id, slug):
    game = get_object_or_404(Game, id=id, slug=slug)
    # увеличить общее число просмотров игр на 1
    # пространство имен формат object-type:id:field
    total_views = r.incr(f"game:{game.id}:views")
    # увеличить рейтинг игр на 1
    # создаём сортированное множество
    r.zincrby("game_ranking", 1, game.id)
    return render(
        request,
        "games/game/detail.html",
        {"section": "games", "game": game, "total_views": total_views},
    )


@login_required
def game_list(request):
    """Выводит постраничный список игр"""
    games = Game.objects.all()
    paginator = Paginator(games, 12)
    page = request.GET.get("page")
    games_only = request.GET.get("games_only")
    try:
        games = paginator.page(page)
    except PageNotAnInteger:
        # Если page_number не целое число, то
        # выдать первую страницу
        games = paginator.page(1)
    except EmptyPage:
        if games_only:
            # Если AJAX-запрос и страница вне диапазона,
            # то вернуть пустую страницу
            return HttpResponse("")
        # Если страница вне диапазона,
        # то вернуть последнюю страницу результатов
        games = paginator.page(paginator.num_pages)
    if games_only:
        return render(
            request, "games/game/list_games.html", {"section": "games", "games": games}
        )
    return render(request, "games/game/list.html", {"section": "games", "games": games})


# Не дает пользователям, не вошедшим в систему, обращаться к этому представлению.
# Этому представлению разрешаются запросы только методом POST.
@login_required
@require_POST
def game_join(request):
    """Представление, которое позволяет пользователям присоед./выйти из игры"""
    game_id = request.POST.get("id")
    # action берется из атрибута action="/submit", если его нет, то есть ещё варианты.
    action = request.POST.get("action")
    if game_id and action:
        try:
            game = Game.objects.get(id=game_id)
            if action == "join":
                # Проверяет лимит присоединений
                if game.joined_players.count() >= game.max_players:
                    messages.error(
                        request, "Максимальное количество игроков достигнуто."
                    )
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Максимальное количество игроков достигнуто.",
                        }
                    )
                # Добавление пользователя в игру
                game.joined_players.add(request.user)
                create_action(request.user, "присоединился(ась) к игре", game)
            else:
                game.joined_players.remove(request.user)
            return JsonResponse({"status": "ok"})
        except Game.DoesNotExist:
            pass
    return JsonResponse({"status": "error"})


# соединить с redis
r = redis.Redis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)


@login_required
def game_ranking(request):
    # получить словарь рейтинга игр
    # Для получения элементов сортированного множества game_ranking исползьуеться zrange()
    game_ranking = r.zrange("game_ranking", 0, -1, desc=True)[:10]
    game_ranking_ids = [int(id) for id in game_ranking]

    # получить наиболее просматриваемые изображения
    most_viewed = list(Game.objects.filter(id__in=game_ranking_ids))
    most_viewed.sort(key=lambda x: game_ranking_ids.index(x.id))
    return render(
        request,
        "games/game/ranking.html",
        {"section": "games", "most_viewed": most_viewed},
    )
