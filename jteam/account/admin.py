from django.contrib import admin

from .models import Friendship, PhoneVerification, Profile, UserBlock


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "phone_verified", "date_of_birth", "photo"]
    list_filter = ["phone_verified"]
    search_fields = ["user__username", "phone"]
    raw_id_fields = ["user"]


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ["phone", "code", "purpose", "created_at", "expires_at", "is_used"]
    list_filter = ["purpose", "is_used"]
    search_fields = ["phone"]


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ["from_user", "to_user", "status", "created"]
    list_filter = ["status"]
    raw_id_fields = ["from_user", "to_user"]


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ["blocker", "blocked", "created"]
    raw_id_fields = ["blocker", "blocked"]
