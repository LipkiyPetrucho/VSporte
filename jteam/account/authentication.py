from django.contrib.auth.models import User

from .models import Profile


class EmailAuthBackend:
    """
    Аутентифицировать посредством адреса электронной почты.
    """

    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password) and user.is_active:
                return user
            return None
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if user.is_active else None


def create_profile(backend, user, *args, **kwargs):
    """Создать профиль пользователя для социальной аутентификации
    Create user profile for social authentication
    """
    Profile.objects.get_or_create(user=user)
