from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from games.models import Game


class Community(models.Model):
    """Группа (сообщество) по интересам."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="owned_communities",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    sport = models.CharField(max_length=255, choices=Game.SPORTS)
    image = models.ImageField(upload_to="images/%Y/%m/%d", blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="joined_communities",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["sport"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "group"
            self.slug = base
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("groups:detail", args=[self.pk, self.slug])


class CommunityJoinRequest(models.Model):
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

    community = models.ForeignKey(
        Community,
        related_name="join_requests",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="community_join_requests",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["community", "user"],
                name="unique_community_join_request",
            ),
        ]
        indexes = [
            models.Index(fields=["community", "status"]),
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user} -> {self.community} ({self.status})"


class CommunityInvitation(models.Model):
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

    community = models.ForeignKey(
        Community,
        related_name="invitations",
        on_delete=models.CASCADE,
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="community_invitations_sent",
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="community_invitations_received",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["community", "to_user"],
                name="unique_community_invitation",
            ),
        ]
        indexes = [
            models.Index(fields=["community", "status"]),
            models.Index(fields=["-created"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return (
            f"{self.from_user} -> {self.to_user} "
            f"({self.community}, {self.status})"
        )
