from django.urls import path
from . import views

app_name = "games"

urlpatterns = [
    path("create/", views.game_create, name="create"),
    path("detail/<int:id>/<slug:slug>/", views.game_detail, name="detail"),
    path("join/", views.game_join, name="join"),
    path("", views.game_list, name="list"),
    path("ranking/", views.game_ranking, name="ranking"),
]
