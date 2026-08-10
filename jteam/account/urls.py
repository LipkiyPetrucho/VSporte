from django.urls import path, include
from . import views

urlpatterns = [
    path(
        "password_change/",
        views.PreferencesPasswordChangeView.as_view(),
        name="password_change",
    ),
    path("login/", views.user_login, name="login"),
    path("", include("django.contrib.auth.urls")),
    path("", views.dashboard, name="dashboard"),
    path("preferences/", views.preferences, name="preferences"),
    path(
        "help/",
        views.help_and_support,
        name="help_and_support",
    ),
    path(
        "preferences/privacy/",
        views.privacy_policy,
        name="privacy_policy",
    ),
    path(
        "preferences/terms/",
        views.terms_of_use,
        name="terms_of_use",
    ),
    path(
        "preferences/delete-account/",
        views.delete_account,
        name="delete_account",
    ),
    path(
        "preferences/deactivate/",
        views.deactivate_account,
        name="deactivate_account",
    ),
    path(
        "preferences/interests/",
        views.select_interests,
        name="select_interests",
    ),
    path(
        "preferences/locations/",
        views.select_location,
        name="select_location",
    ),
    path(
        "preferences/locations/save/",
        views.save_location,
        name="save_location",
    ),
    path(
        "preferences/locations/recent/delete/",
        views.delete_recent_location_view,
        name="delete_recent_location",
    ),
    path("register/", views.register, name="register"),
    path("edit/", views.edit, name="edit"),
    path("edit/phone/verify/", views.edit_phone_verify, name="edit_phone_verify"),
    path("users/", views.user_list, name="user_list"),
    path("users/follow", views.user_follow, name="user_follow"),
    path("users/friendship", views.user_friendship, name="user_friendship"),
    path("users/block", views.user_block, name="user_block"),
    path(
        "preferences/blocked/",
        views.blocked_users,
        name="blocked_users",
    ),
    path(
        "preferences/notifications/",
        views.notification_settings,
        name="notification_settings",
    ),
    path(
        "preferences/notifications/update/",
        views.update_notification_setting,
        name="update_notification_setting",
    ),
    path(
        "preferences/contacts/",
        views.contact_visibility,
        name="contact_visibility",
    ),
    path(
        "preferences/contacts/update/",
        views.update_contact_visibility,
        name="update_contact_visibility",
    ),
    path("users/<username>/", views.user_detail, name="user_detail"),
    path("search/", views.account_search, name="account_search"),
]
