from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from datetime import timedelta


def validate_future_datetime(value):
    """Проверяет, что дата и время в будущем"""
    now = timezone.localtime(timezone.now())
    if value < now:
        raise ValidationError("Время начала игры должно быть в будущем")
    # Округляем время до минут
    if value.second != 0 or value.microsecond != 0:
        raise ValidationError("Время должно быть указано с точностью до минут")


class Game(models.Model):
    """Модель, представляющая игру."""

    SPORTS = (
        ("football", "футбол"),
        ("tennis", "теннис"),
        ("bowling", "боулинг"),
        ("beach volleyball", "пляжный волейбол"),
        ("volleyball", "волейбол"),
        ("ice hockey", "хоккей на льду"),
        ("chess", "шахматы"),
    )
    SPORT_ICONS = {
        "football": "football-icon.png",
        "tennis": "tennis-icon.png",
        "ice hockey": "hockey-icon.png",
        # Добавьте другие виды спорта и соответствующие иконки
    }

    CHOICES = (
        ("open", "Open"),
        ("started", "Started"), 
        ("finished", "Finished")
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_games_created",
        on_delete=models.CASCADE,
    )
    sport = models.CharField(max_length=255, choices=SPORTS)
    place = models.CharField(max_length=255)
    start_time = models.DateTimeField(
        default=timezone.now,
        validators=[validate_future_datetime]
    )
    duration = models.DurationField(
        default=timedelta(hours=1),
        help_text="Продолжительность игры (чч:мм)"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_players = models.PositiveIntegerField(default=2)
    joined_players = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="joined_games", blank=True
    )
    status = models.CharField(max_length=255, choices=CHOICES, default="open")
    slug = models.SlugField(max_length=200)
    image = models.ImageField(upload_to="images/%Y/%m/%d", blank=True)

    class Meta:
        """
        Мета-класс для модели Game.

        Определяет:
            * `verbose_name`: Отображение названия модели
             в единственном числе (админ-панель и т.д.).
            * `verbose_name_plural`: Отображение названия модели
             во множественном числе (админ-панель и т.д.).
            * `indexes`: Индексы для полей модели для улучшения производительности запросов.
            * `ordering`: Порядок по умолчанию для объектов модели при их получении.
        """

        verbose_name = "Игра"
        verbose_name_plural = "Игры"
        indexes = [
            models.Index(fields=["created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        """Возвращает строковое представление игры."""
        return f"{self.sport} {timezone.localtime(self.start_time).strftime('%Y-%m-%d %H:%M')} {self.place}"

    def clean(self):
        """Дополнительная валидация модели"""
        super().clean()
        # Округляем время до минут
        if self.start_time:
            self.start_time = self.start_time.replace(second=0, microsecond=0)

    def save(self, *args, **kwargs):
        """Сохраняет игру.
        Если слаг не задан, генерирует его из названия вида спорта, даты и места.
        """
        if not self.slug:
            self.slug = (
                slugify(self.sport, allow_unicode=True)
                + "-"
                + slugify(timezone.localtime(self.start_time).strftime('%Y-%m-%d'), allow_unicode=True)
                + "-"
                + slugify(timezone.localtime(self.created_at).strftime('%Y-%m-%d %H:%M'), allow_unicode=True)
                + "-"
                + slugify(str(self.user), allow_unicode=True)
            )
        self.clean()  # Вызываем clean() перед сохранением
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Возвращает URL-адрес страницы детального отображения игры."""
        return reverse("games:detail", args=[self.pk, self.slug])

    # ...Можно добавить проверку на существование игры перед генерацией URL-адреса.

    # models.py:

    # Подсчет оставшихся слотов.
    # Проверка доступности игры.
    # views.py:
    # Обработка запроса на вступление в игру.
    # Отображение списка доступных игр.
