from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User

from .interests import INTEREST_CHOICES
from .models import Profile
from .phone_service import PhoneValidationError, normalize_phone


class PreferencesPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Пароль"
        self.fields["old_password"].widget.attrs.update(
            {
                "class": "password-update__input",
                "autocomplete": "current-password",
            }
        )
        self.fields["new_password1"].label = "Новый пароль"
        self.fields["new_password1"].help_text = ""
        self.fields["new_password1"].widget.attrs.update(
            {
                "class": "password-update__input",
                "placeholder": "Введите новый пароль",
                "autocomplete": "new-password",
            }
        )
        self.fields["new_password2"].label = "Подтвердите пароль"
        self.fields["new_password2"].widget.attrs.update(
            {
                "class": "password-update__input",
                "placeholder": "Введите новый пароль еще раз",
                "autocomplete": "new-password",
            }
        )


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class EmailLoginForm(forms.Form):
    """Вход по email или логину."""

    login = forms.CharField(
        label="Email или логин",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Email или логин",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Пароль",
                "autocomplete": "current-password",
            }
        ),
    )

    def clean_login(self):
        value = (self.cleaned_data.get("login") or "").strip()
        if not value:
            raise forms.ValidationError("Укажите email или логин.")
        return value


class UserRegistrationForm(forms.Form):
    username = forms.CharField(
        label="Логин",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Логин *",
                "autocomplete": "username",
            }
        ),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email *",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Пароль *",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Подтверждение пароля *",
                "autocomplete": "new-password",
            }
        ),
    )
    first_name = forms.CharField(
        label="Имя",
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Имя (необязательно)",
                "autocomplete": "given-name",
            }
        ),
    )
    phone = forms.CharField(
        label="Телефон",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Телефон (необязательно)",
                "autocomplete": "tel",
                "inputmode": "tel",
            }
        ),
    )

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Укажите логин.")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Этот логин уже занят.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            raise forms.ValidationError("Укажите email.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already in use.")
        return email

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        if not raw:
            return None
        try:
            phone = normalize_phone(raw)
        except PhoneValidationError as exc:
            raise forms.ValidationError(str(exc)) from exc
        if Profile.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Этот номер телефона уже используется.")
        return phone

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password") or ""
        password2 = cleaned.get("password2") or ""
        if password != password2:
            self.add_error("password2", "Пароли не совпадают.")
        return cleaned


class PhoneVerificationForm(forms.Form):
    code = forms.CharField(
        label="Код подтверждения",
        max_length=4,
        min_length=4,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Код из SMS",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{4}",
                "maxlength": "4",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit() or len(code) != 4:
            raise forms.ValidationError("Введите четырёхзначный код.")
        return code


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "profile-edit__input", "autocomplete": "given-name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "profile-edit__input", "autocomplete": "family-name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "profile-edit__input", "autocomplete": "email"}
            ),
        }

    def clean_email(self):
        data = (self.cleaned_data.get("email") or "").strip()
        if not data:
            raise forms.ValidationError("Укажите email.")
        qs = User.objects.exclude(id=self.instance.id).filter(email=data)
        if qs.exists():
            raise forms.ValidationError("Email already in use.")
        return data


class InterestsForm(forms.Form):
    interests = forms.MultipleChoiceField(
        choices=INTEREST_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )


class ProfileEditForm(forms.ModelForm):
    interests = forms.MultipleChoiceField(
        choices=INTEREST_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )
    phone = forms.CharField(
        label="Телефон",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "profile-edit__input",
                "autocomplete": "tel",
                "inputmode": "tel",
                "placeholder": "+7XXXXXXXXXX",
            }
        ),
    )

    class Meta:
        model = Profile
        fields = ["photo", "gender", "bio", "show_email", "show_phone"]
        widgets = {
            "photo": forms.FileInput(
                attrs={
                    "class": "profile-edit__photo-input",
                    "accept": "image/*",
                    "id": "profile-photo-input",
                }
            ),
            "gender": forms.Select(
                attrs={"class": "profile-edit__input profile-edit__select"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "profile-edit__textarea",
                    "rows": 4,
                    "placeholder": "Расскажите о себе",
                }
            ),
            "show_email": forms.CheckboxInput(
                attrs={"class": "profile-edit__toggle-input"}
            ),
            "show_phone": forms.CheckboxInput(
                attrs={"class": "profile-edit__toggle-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gender"].choices = list(Profile.GENDER_CHOICES)
        if self.instance.pk:
            self.fields["interests"].initial = self.instance.interests or []
            self.fields["phone"].initial = self.instance.phone or ""

    def clean_phone(self):
        raw = self.cleaned_data.get("phone", "").strip()
        if not raw:
            return None
        try:
            phone = normalize_phone(raw)
        except PhoneValidationError as exc:
            raise forms.ValidationError(str(exc)) from exc
        qs = Profile.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Этот номер телефона уже используется.")
        return phone

    def save(self, commit=True):
        """Сохраняет профиль без изменения телефона (телефон — только после OTP)."""
        profile = super().save(commit=False)
        profile.interests = self.cleaned_data.get("interests", [])
        if commit:
            profile.save()
        return profile


class SearchForm(forms.Form):
    query = forms.CharField(
        label="",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Введите имя игрока",
                "class": "form-control form-control-width",
                "style": "background-color: #f8f9fa; border-radius: 5px;",
            }
        ),
    )
