from django.contrib.auth import get_user_model
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.urls import reverse


class Profile(models.Model):
    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_CHOICES = (
        ("", "Не указан"),
        (GENDER_MALE, "Мужской"),
        (GENDER_FEMALE, "Женский"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE
    )
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to="users/%Y/%m/%d/",
        blank=True,
        default="default-profile-user.jpg",
    )
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True, default=""
    )
    bio = models.TextField(blank=True)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Телефон",
    )
    phone_verified = models.BooleanField(default=False)
    show_email = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    show_gender = models.BooleanField(default=True)
    interests = models.JSONField(default=list, blank=True)
    location_title = models.CharField(max_length=255, blank=True)
    location_address = models.CharField(max_length=512, blank=True)
    location_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    location_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    recent_locations = models.JSONField(default=list, blank=True)
    notify_game_reminders = models.BooleanField(default=True)
    notify_chat_messages = models.BooleanField(default=True)
    notify_activity_updates = models.BooleanField(default=True)
    notify_social_updates = models.BooleanField(default=True)

    NOTIFICATION_PREF_FIELDS = (
        "notify_game_reminders",
        "notify_chat_messages",
        "notify_activity_updates",
        "notify_social_updates",
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def get_absolute_url(self):
        return reverse("user_detail", args=[str(self.id)])


class PhoneVerification(models.Model):
    PURPOSE_REGISTER = "register"
    PURPOSE_CHANGE = "change"
    PURPOSE_LOGIN = "login"
    PURPOSE_CHOICES = (
        (PURPOSE_REGISTER, "Регистрация"),
        (PURPOSE_CHANGE, "Смена телефона"),
        (PURPOSE_LOGIN, "Вход"),
    )

    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=4)
    purpose = models.CharField(
        max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_REGISTER
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["phone", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone} ({self.purpose})"

    @property
    def is_expired(self):
        from django.utils import timezone

        return timezone.now() >= self.expires_at


class Friendship(models.Model):
    PENDING = "pending"
    ACCEPTED = "accepted"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
    )

    from_user = models.ForeignKey(
        "auth.User",
        related_name="friendships_sent",
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        "auth.User",
        related_name="friendships_received",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="unique_friendship_request",
            ),
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocks_sent",
        on_delete=models.CASCADE,
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="blocks_received",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_user_block",
            ),
        ]
        indexes = [
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


class Contact(models.Model):
    user_from = models.ForeignKey(
        "auth.User", related_name="rel_from_set", on_delete=models.CASCADE
    )
    user_to = models.ForeignKey(
        "auth.User", related_name="rel_to_set", on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user_from} joined {self.user_to}"


# Добавление поле в User динамически
user_model = get_user_model()
user_model.add_to_class(
    "following",
    models.ManyToManyField(
        "self", through=Contact, related_name="followers", symmetrical=False
    ),
)
user_model.add_to_class(
    "blocking",
    models.ManyToManyField(
        "self",
        through=UserBlock,
        through_fields=("blocker", "blocked"),
        related_name="blocked_by",
        symmetrical=False,
    ),
)
