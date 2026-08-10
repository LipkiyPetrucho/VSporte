from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from account.models import PhoneVerification, Profile
from account.phone_service import (
    PhoneValidationError,
    create_and_send_code,
    generate_username_from_phone,
    normalize_phone,
    verify_code,
)


class SocialAuthConfigTests(TestCase):
    def test_facebook_backend_removed(self):
        backends = settings.AUTHENTICATION_BACKENDS
        self.assertFalse(
            any("facebook" in backend.lower() for backend in backends)
        )

    def test_telegram_backend_configured(self):
        self.assertIn(
            "social_core.backends.telegram.TelegramAuth",
            settings.AUTHENTICATION_BACKENDS,
        )


@override_settings(
    ALLOWED_HOSTS=["localhost", "testserver"],
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    PHONE_CODE_RESEND_COOLDOWN=0,
    SMS_BACKEND="console",
)
class PhoneServiceTests(TestCase):
    def test_normalize_phone_variants(self):
        self.assertEqual(normalize_phone("89991234567"), "+79991234567")
        self.assertEqual(normalize_phone("9991234567"), "+79991234567")
        self.assertEqual(normalize_phone("+7 (999) 123-45-67"), "+79991234567")

    def test_normalize_phone_invalid(self):
        with self.assertRaises(PhoneValidationError):
            normalize_phone("123")

    def test_create_and_verify_code(self):
        verification = create_and_send_code(
            "+79990001122", purpose=PhoneVerification.PURPOSE_CHANGE
        )
        self.assertEqual(len(verification.code), 4)
        self.assertTrue(verification.code.isdigit())
        verify_code(
            "+79990001122",
            verification.code,
            purpose=PhoneVerification.PURPOSE_CHANGE,
        )
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)

    def test_wrong_code_increments_attempts(self):
        verification = create_and_send_code(
            "+79990001133", purpose=PhoneVerification.PURPOSE_CHANGE
        )
        with self.assertRaises(PhoneValidationError):
            verify_code(
                "+79990001133",
                "0000" if verification.code != "0000" else "1111",
                purpose=PhoneVerification.PURPOSE_CHANGE,
            )
        verification.refresh_from_db()
        self.assertEqual(verification.attempts, 1)

    def test_expired_code_rejected(self):
        verification = create_and_send_code(
            "+79990001144", purpose=PhoneVerification.PURPOSE_CHANGE
        )
        PhoneVerification.objects.filter(pk=verification.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        with self.assertRaises(PhoneValidationError):
            verify_code(
                "+79990001144",
                verification.code,
                purpose=PhoneVerification.PURPOSE_CHANGE,
            )

    def test_generate_username_from_phone(self):
        username = generate_username_from_phone("+79990001155")
        self.assertEqual(username, "user_79990001155")
        User.objects.create(username=username)
        username2 = generate_username_from_phone("+79990001155")
        self.assertEqual(username2, "user_79990001155_1")


@override_settings(
    ALLOWED_HOSTS=["localhost", "testserver"],
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    PHONE_CODE_RESEND_COOLDOWN=0,
    SMS_BACKEND="console",
)
class RegistrationFlowTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")

    def test_register_requires_email_and_password(self):
        response = self.client.post(
            reverse("register"),
            {"username": "onlyuser", "phone": "9001112233"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="onlyuser").exists())

    def test_register_with_email_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "player_one",
                "first_name": "Иван",
                "email": "ivan@example.com",
                "password": "StrongPass123",
                "password2": "StrongPass123",
                "phone": "9002223344",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/register_done.html")
        user = User.objects.get(username="player_one")
        self.assertEqual(user.email, "ivan@example.com")
        self.assertEqual(user.first_name, "Иван")
        self.assertTrue(user.check_password("StrongPass123"))
        self.assertEqual(user.profile.phone, "+79002223344")
        self.assertFalse(user.profile.phone_verified)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username="exists", email="taken@example.com", password="x"
        )
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "taken@example.com",
                "password": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email already in use")


@override_settings(
    ALLOWED_HOSTS=["localhost", "testserver"],
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    PHONE_CODE_RESEND_COOLDOWN=0,
    SMS_BACKEND="console",
)
class LoginFlowTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")
        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="EmailPass123",
        )

    def test_login_via_email_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "login": "login@example.com",
                "password": "EmailPass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_login_via_username_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "login": "loginuser",
                "password": "EmailPass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_email_login_wrong_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "login": "login@example.com",
                "password": "wrong",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Неверный логин/email или пароль")

    def test_phone_login_route_removed(self):
        response = self.client.get("/login/verify/")
        self.assertEqual(response.status_code, 404)


@override_settings(
    ALLOWED_HOSTS=["localhost", "testserver"],
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    PHONE_CODE_RESEND_COOLDOWN=0,
    SMS_BACKEND="console",
)
class PhoneChangeFlowTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")
        self.user = User.objects.create_user(
            username="changer",
            email="changer@example.com",
            password="ChangePass123",
        )
        Profile.objects.filter(user=self.user).update(
            phone="+79005556677", phone_verified=True
        )
        self.client.login(username="changer", password="ChangePass123")

    def _latest_code(self, phone, purpose=PhoneVerification.PURPOSE_CHANGE):
        return (
            PhoneVerification.objects.filter(phone=phone, purpose=purpose)
            .order_by("-created_at")
            .first()
            .code
        )

    def test_phone_change_requires_confirmation(self):
        response = self.client.post(
            reverse("edit"),
            {
                "first_name": "Changer",
                "last_name": "",
                "email": "changer@example.com",
                "phone": "9006667788",
                "gender": "",
                "bio": "",
                "show_email": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit_phone_verify"))

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, "+79005556677")
        self.assertTrue(self.user.profile.phone_verified)

        code = self._latest_code("+79006667788")
        response = self.client.post(
            reverse("edit_phone_verify"),
            {"action": "verify", "code": code},
        )
        self.assertEqual(response.status_code, 302)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, "+79006667788")
        self.assertTrue(self.user.profile.phone_verified)

    def test_phone_not_changed_without_code(self):
        self.client.post(
            reverse("edit"),
            {
                "first_name": "Changer",
                "last_name": "",
                "email": "changer@example.com",
                "phone": "9007778899",
                "gender": "",
                "bio": "",
            },
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, "+79005556677")

    @patch("account.views.create_and_send_code")
    def test_same_phone_does_not_trigger_otp(self, mocked_send):
        response = self.client.post(
            reverse("edit"),
            {
                "first_name": "Changer",
                "last_name": "",
                "email": "changer@example.com",
                "phone": "9005556677",
                "gender": "",
                "bio": "hello",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse("edit_phone_verify"))
        mocked_send.assert_not_called()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, "hello")
