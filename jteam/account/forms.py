from django import forms
from django.contrib.auth.models import User

from .interests import INTEREST_CHOICES
from .models import Profile


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repeat password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "first_name", "email"]

    def clean_password2(self):
        cd = self.cleaned_data
        if cd["password"] != cd["password2"]:
            raise forms.ValidationError("Password don't match.")
        return cd["password2"]

    def clean_email(self):
        data = self.cleaned_data["email"]
        if User.objects.filter(email=data).exists():
            raise forms.ValidationError("Email already in use.")
        return data


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
        data = self.cleaned_data["email"]
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

    class Meta:
        model = Profile
        fields = ["photo", "gender", "bio", "show_email"]
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Model choices already include the blank "Не указан" option.
        self.fields["gender"].choices = list(Profile.GENDER_CHOICES)
        if self.instance.pk:
            self.fields["interests"].initial = self.instance.interests or []

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.interests = self.cleaned_data.get("interests", [])
        if commit:
            profile.save()
        return profile


# возможность вводить поисковые запросы
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
