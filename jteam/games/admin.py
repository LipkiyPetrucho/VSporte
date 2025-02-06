from django.contrib import admin

from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """field for admin"""

    list_display = ["sport", "max_players", "place", "created_at", "slug"]
    list_filter = ["created_at"]
