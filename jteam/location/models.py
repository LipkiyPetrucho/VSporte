from django.db import models
from django.urls import reverse


class City(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]
        verbose_name = "city"
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("location:place_list_by_city", args=[self.slug])


class Place(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    city = models.ForeignKey(City, related_name="places", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="places/%Y/%m/%d", blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["id", "slug"]),
            models.Index(fields=["name"]),
            models.Index(fields=["-created"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("location:place_detail", args=[self.id, self.slug])
