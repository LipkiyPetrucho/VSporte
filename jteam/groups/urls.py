from django.urls import path

from . import views

app_name = "groups"

urlpatterns = [
    path("create/", views.community_create, name="create"),
    path(
        "detail/<int:id>/<slug:slug>/edit/",
        views.community_edit,
        name="edit",
    ),
    path(
        "detail/<int:id>/<slug:slug>/",
        views.community_detail,
        name="detail",
    ),
    path("join/", views.community_join, name="join"),
    path("leave/", views.community_leave, name="leave"),
    path("membership/", views.community_membership, name="membership"),
    path("invite/", views.community_invite, name="invite"),
    path("delete/<int:id>/", views.community_delete, name="delete"),
    path("", views.community_list, name="list"),
]
