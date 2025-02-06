from django.urls import path
from . import views

app_name = "location"

urlpatterns = [
    path("", views.place_list, name="list"),
    path("list/<slug:city_slug>/", views.place_list, name="place_list_by_city"),
    path("place_detail/<int:id>/<slug:slug>/", views.place_detail, name="place_detail"),
]
