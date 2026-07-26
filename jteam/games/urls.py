from django.urls import path
from . import views

app_name = "games"

urlpatterns = [
    path("create/", views.game_create, name="create"),
    path(
        "detail/<int:id>/<slug:slug>/edit/",
        views.game_edit,
        name="edit",
    ),
    path(
        "detail/<int:id>/<slug:slug>/chat/",
        views.game_chat,
        name="chat",
    ),
    path(
        "detail/<int:id>/<slug:slug>/chat/messages/",
        views.game_chat_messages,
        name="chat_messages",
    ),
    path(
        "detail/<int:id>/<slug:slug>/organizer-settings/",
        views.game_organizer_settings,
        name="organizer_settings",
    ),
    path("detail/<int:id>/<slug:slug>/", views.game_detail, name="detail"),
    path("status/<int:id>/", views.game_status, name="status"),
    path("join/", views.game_join, name="join"),
    path("participation/", views.game_participation, name="participation"),
    path("invite/", views.game_invite, name="invite"),
    path("", views.game_list, name="list"),
    path("ranking/", views.game_ranking, name="ranking"),
    path("delete/<int:id>/", views.game_delete, name="delete"),
]
