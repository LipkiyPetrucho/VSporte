from django.contrib.auth import get_user_model
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.urls import reverse


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE
    )
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to="users/%Y/%m/%d/",
        blank=True,
        default="default-profile-user.jpg",
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def get_absolute_url(self):
        return reverse("user_detail", args=[str(self.id)])


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
