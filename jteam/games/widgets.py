from django.forms import TextInput
from django.utils import timezone

class CustomDateTimeInput(TextInput):
    """Кастомный виджет для ввода даты и времени в формате dd.mm.yyyy HH:MM"""
    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs.update({
            'placeholder': 'дд.мм.гггг чч:мм (например: 14.03.2025 13:00)',
            'class': 'form-control form-control-width',
            'style': 'background-color: #f8f9fa; border-radius: 5px;',
        })
        super().__init__(attrs)

    def format_value(self, value):
        """Форматирует значение для отображения в форме"""
        if isinstance(value, str):
            return value
        if value:
            # Преобразуем datetime в строку нужного формата
            return timezone.localtime(value).strftime('%d.%m.%Y %H:%M')
        return ''
