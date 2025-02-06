from django import forms
from django.forms import Select, TextInput, NumberInput, Textarea, ClearableFileInput

from .models import Game


class GameCreateForm(forms.ModelForm):
    """
    Форма создания игры.

    """

    class Meta:
        model = Game
        fields = [
            "sport",
            "place",
            "date",
            "start_time",
            "duration",
            "max_players",
            "price",
            "description",
            "image",
        ]
        labels = {
            "sport": "Вид спорта",
            "place": "Место игры",
            "date": "Дата игры",
            "start_time": "Время начала игры",
            "duration": "Продолжительность",
            "max_players": "Количество игроков",
            "price": "Цена игры",
            "description": "Описание",
            "image": "Обложка",
        }

        widgets = {
            "sport": Select(
                attrs={
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "place": TextInput(
                attrs={
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "max_players": NumberInput(
                attrs={
                    "class": "form-control form-control-width",
                    "step": "1",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "description": Textarea(
                attrs={
                    "cols": 30,
                    "rows": 3,
                    "class": "form-control form-control-width",
                    "type": "text",
                    "placeholder": "Опишите например: есть душевые, есть парковочные места",
                    "aria-label": "default input example",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "price": NumberInput(
                attrs={
                    "step": "10",
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "duration": TextInput(
                attrs={
                    "placeholder": "HH:MM",
                    "type": "time",
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "date": TextInput(
                attrs={
                    "placeholder": "HH:MM",
                    "type": "date",
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "start_time": TextInput(
                attrs={
                    "placeholder": "HH:MM",
                    "type": "time",
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
            "image": ClearableFileInput(
                attrs={
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
        }
