from django.contrib import admin

from .models import City, Place


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "price", "available", "created", "updated"]
    list_filter = ["available", "created", "updated"]
    list_editable = ["price", "available"]
    prepopulated_fields = {"slug": ("name",)}
