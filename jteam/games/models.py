from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
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

    SKILL_LEVELS = (
        ("beginner", "Начинающий"),
        ("intermediate", "Средний"),
        ("advanced", "Продвинутый"),
        ("pro", "Профи"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="user_games_created",
        on_delete=models.CASCADE,
    )
    sport = models.CharField(max_length=255, choices=SPORTS)
    place = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_time = models.DateTimeField(
        default=timezone.now,
        validators=[validate_future_datetime]
    )
    duration = models.DurationField(
        default=timedelta(hours=1),
        help_text="Продолжительность игры (чч:мм)"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_players = models.PositiveIntegerField(default=2)
    extra_players = models.PositiveIntegerField(
        default=0,
        help_text="Доп. участники, которых организатор приводит офлайн",
    )
    has_skill_level = models.BooleanField(default=False)
    skill_level = models.CharField(
        max_length=20,
        choices=SKILL_LEVELS,
        blank=True,
        default="",
    )
    place_reserved = models.BooleanField(default=False)
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

    def get_chat_url(self):
        """Возвращает URL-адрес страницы чата игры."""
        return reverse("games:chat", args=[self.pk, self.slug])

    def compute_status(self, now=None):
        """Вычисляет актуальный статус игры по времени начала и продолжительности."""
        now = now or timezone.now()
        end_time = self.start_time + self.duration
        if now >= end_time:
            return "finished"
        if now >= self.start_time:
            return "started"
        return "open"

    def sync_status(self, save=True):
        """Синхронизирует поле status с текущим временем."""
        new_status = self.compute_status()
        if self.status != new_status:
            self.status = new_status
            if save:
                self.save(update_fields=["status"])
        return self.status

    def get_formatted_duration(self):
        """Возвращает продолжительность игры в читаемом формате (например, '2 ч 30 мин')."""
        if not self.duration:
            return "Не указано"
        
        # Получаем общее количество секунд из timedelta объекта
        total_seconds = int(self.duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        result = []
        if hours > 0:
            result.append(f"{hours} ч")
        if minutes > 0:
            result.append(f"{minutes} мин")
        
        return " ".join(result) if result else "0 мин"

    def user_can_access_chat(self, user):
        """True, если пользователь — организатор или участник игры (доступ к чату)."""
        if not getattr(user, "is_authenticated", False):
            return False
        if user.pk == self.user_id:
            return True
        return self.joined_players.filter(pk=user.pk).exists()

    def joined_count(self):
        return self.joined_players.count()

    def occupied_seats(self):
        """Занятые места: онлайн-участники + доп. участники организатора."""
        return self.joined_count() + self.extra_players

    def available_seats(self):
        """Свободные места с учётом доп. участников организатора."""
        return max(0, self.max_players - self.occupied_seats())

    def is_full(self):
        return self.available_seats() == 0

    # ...Можно добавить проверку на существование игры перед генерацией URL-адреса.


class GameMessage(models.Model):
    """Сообщение в чате игры."""

    game = models.ForeignKey(
        Game,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="game_messages",
        on_delete=models.CASCADE,
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"
        indexes = [
            models.Index(fields=["game", "created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} @ {self.game_id}: {self.text[:50]}"


class GameParticipationRequest(models.Model):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
    )

    game = models.ForeignKey(
        Game,
        related_name="participation_requests",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="game_participation_requests",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "user"],
                name="unique_game_participation_request",
            ),
        ]
        indexes = [
            models.Index(fields=["game", "status"]),
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user} -> {self.game} ({self.status})"


class GameInvitation(models.Model):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
        (CANCELLED, "Cancelled"),
    )

    game = models.ForeignKey(
        Game,
        related_name="invitations",
        on_delete=models.CASCADE,
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="game_invitations_sent",
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="game_invitations_received",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "to_user"],
                name="unique_game_invitation",
            ),
        ]
        indexes = [
            models.Index(fields=["game", "status"]),
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.game}, {self.status})"
