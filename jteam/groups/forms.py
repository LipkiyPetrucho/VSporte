from django import forms
from django.forms import Select, Textarea, ClearableFileInput, TextInput

from games.models import Game

from .models import Community


class CommunityCreateForm(forms.ModelForm):
    """Форма создания группы."""

    class Meta:
        model = Community
        fields = ["name", "sport", "description", "image"]
        labels = {
            "name": "Название",
            "sport": "Вид спорта",
            "description": "Описание",
            "image": "Фото",
        }
        widgets = {
            "name": TextInput(
                attrs={
                    "class": "form-field",
                    "placeholder": "Название группы",
                }
            ),
            "sport": Select(
                attrs={
                    "class": "form-field",
                }
            ),
            "description": Textarea(
                attrs={
                    "class": "form-field",
                    "rows": 4,
                    "placeholder": "О чём группа, правила вступления...",
                }
            ),
            "image": ClearableFileInput(
                attrs={
                    "class": "form-field-file",
                    "accept": "image/*",
                }
            ),
        }


class CommunityEditForm(CommunityCreateForm):
    """Форма редактирования группы."""


class CommunityFilterForm(forms.Form):
    sport = forms.ChoiceField(
        choices=[("", "Все виды спорта")] + list(Game.SPORTS),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "groups-page-filter__control",
            }
        ),
    )
