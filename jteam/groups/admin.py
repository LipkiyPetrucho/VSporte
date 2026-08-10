from django.contrib import admin

from .models import Community, CommunityInvitation, CommunityJoinRequest


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ["name", "sport", "owner", "created_at", "slug"]
    list_filter = ["sport", "created_at"]
    search_fields = ["name", "description", "owner__username"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["members"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CommunityJoinRequest)
class CommunityJoinRequestAdmin(admin.ModelAdmin):
    list_display = ["community", "user", "status", "created"]
    list_filter = ["status", "created"]
    search_fields = ["community__name", "user__username"]


@admin.register(CommunityInvitation)
class CommunityInvitationAdmin(admin.ModelAdmin):
    list_display = ["community", "from_user", "to_user", "status", "created"]
    list_filter = ["status", "created"]
    search_fields = [
        "community__name",
        "from_user__username",
        "to_user__username",
    ]
