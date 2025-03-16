from django import forms
from django.forms import Select, TextInput, NumberInput, Textarea, ClearableFileInput, DateField, DateTimeInput
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError

from .models import Game
from .widgets import CustomDateTimeInput

class GameCreateForm(forms.ModelForm):
    """
    Форма создания игры.

    """
    # Переопределяем поле start_time как строковое
    start_time = forms.CharField(
        label="Время начала игры",
        help_text="Формат: дд.мм.гггг чч:мм (например: 14.03.2025 13:00)",
        widget=CustomDateTimeInput()
    )

    # Переопределяем поле duration как строковое
    duration = forms.CharField(
        label="Продолжительность",
        help_text="Формат: чч:мм (например: 01:30 для 1 часа 30 минут)",
        widget=TextInput(
            attrs={
                "class": "form-control form-control-width",
                "placeholder": "Например: 01:30",
                "style": "background-color: #f8f9fa; border-radius: 5px;",
            }
        )
    )

    class Meta:
        model = Game
        fields = [
            "sport",
            "place",
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
                    "min": "2",  # Минимум 2 игрока
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
            "image": ClearableFileInput(
                attrs={
                    "class": "form-control form-control-width",
                    "style": "background-color: #f8f9fa; border-radius: 5px;",
                }
            ),
        }

    def clean_start_time(self):
        """Преобразование строки даты и времени в datetime"""
        start_time = self.cleaned_data.get('start_time')
        if start_time:
            try:
                # Преобразуем строку в datetime
                dt = datetime.strptime(start_time, '%d.%m.%Y %H:%M')
                # Добавляем информацию о временной зоне
                dt = timezone.make_aware(dt)
                # Проверяем, что дата в будущем
                if dt <= timezone.now():
                    raise forms.ValidationError("Время начала игры должно быть в будущем")
                return dt
            except ValueError:
                raise forms.ValidationError("Неверный формат даты и времени. Используйте формат дд.мм.гггг чч:мм")
        return start_time

    def clean_duration(self):
        """Преобразование строки продолжительности в timedelta"""
        duration = self.cleaned_data.get('duration')
        if duration:
            try:
                # Разбиваем строку на часы и минуты
                hours, minutes = map(int, duration.split(':'))
                if hours < 0 or minutes < 0 or minutes >= 60:
                    raise ValidationError("Неверный формат продолжительности")
                # Преобразуем в timedelta
                return timedelta(hours=hours, minutes=minutes)
            except ValueError:
                raise ValidationError("Укажите продолжительность в формате ЧЧ:ММ (например: 01:30)")
        return duration
