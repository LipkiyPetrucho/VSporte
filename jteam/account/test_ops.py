from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from jteam.settings.error_reporting import (
    apply_prod_error_logging,
    init_sentry,
    sentry_traces_sample_rate,
    warn_if_no_error_reporting,
)
from jteam.prod_smoke import (
    FetchResult,
    check_csrf_on_login,
    check_debug_false,
    check_debug_toolbar,
    check_hashed_static,
    check_http_redirects_to_https,
    check_https_home,
    check_secure_cookies,
    run_checks,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _result(status=200, headers=None, body="", url="https://jteam.ru/"):
    return FetchResult(status, headers or {}, body, url)


class ProdErrorReportingTests(SimpleTestCase):
    def test_mail_admins_handler_wired(self):
        logging_config = {
            "version": 1,
            "handlers": {
                "console": {"class": "logging.StreamHandler"},
                "file": {"class": "logging.StreamHandler"},
            },
            "loggers": {},
        }
        apply_prod_error_logging(logging_config)
        handler = logging_config["handlers"]["mail_admins"]
        self.assertEqual(
            handler["class"], "django.utils.log.AdminEmailHandler"
        )
        self.assertIn("require_debug_false", handler["filters"])
        for name in ("django.request", "django.security", "celery"):
            self.assertIn("mail_admins", logging_config["loggers"][name]["handlers"])

    def test_init_sentry_noop_without_dsn(self):
        self.assertFalse(init_sentry(""))
        self.assertFalse(init_sentry("   "))

    def test_init_sentry_requires_package_when_dsn_set(self):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "sentry_sdk" or name.startswith("sentry_sdk."):
                raise ImportError("sentry-sdk missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with self.assertRaises(RuntimeError):
                init_sentry("https://example@o123.ingest.sentry.io/1")

    def test_prod_settings_wire_alerting(self):
        text = (
            REPO_ROOT / "jteam" / "jteam" / "settings" / "prod.py"
        ).read_text(encoding="utf-8")
        self.assertIn("apply_prod_error_logging", text)
        self.assertIn("init_sentry", text)
        self.assertIn("AdminEmailHandler", (
            REPO_ROOT / "jteam" / "jteam" / "settings" / "error_reporting.py"
        ).read_text(encoding="utf-8"))

    def test_warn_if_neither_admins_nor_sentry(self):
        with self.assertWarns(RuntimeWarning):
            warn_if_no_error_reporting([], "")

    def test_no_warning_when_admins_or_sentry_set(self):
        with patch("jteam.settings.error_reporting.warnings.warn") as warn:
            warn_if_no_error_reporting([("Admin", "a@example.com")], "")
            warn_if_no_error_reporting([], "https://example@o123.ingest.sentry.io/1")
        warn.assert_not_called()

    def test_traces_sample_rate_invalid_defaults_to_zero(self):
        with patch.dict("os.environ", {"SENTRY_TRACES_SAMPLE_RATE": "nope"}):
            self.assertEqual(sentry_traces_sample_rate(), 0.0)


class BackupScriptsTests(SimpleTestCase):
    def test_backup_script_uses_pg_dump_and_rotation(self):
        script = (REPO_ROOT / "scripts" / "backup-postgres.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("pg_dump -Fc", script)
        self.assertIn("BACKUP_KEEP_DAYS", script)
        self.assertIn("-mtime", script)

    def test_restore_requires_confirm(self):
        script = (REPO_ROOT / "scripts" / "restore-postgres.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("CONFIRM", script)
        self.assertIn("pg_restore", script)

    def test_prod_compose_defines_backup_service(self):
        compose = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn("backup:", compose)
        self.assertIn("backup-postgres.sh", compose)
        self.assertIn("./backups:/backups", compose)


class ProdSmokeLogicTests(SimpleTestCase):
    def test_https_home_ok(self):
        ok, _ = check_https_home(_result(200))
        self.assertTrue(ok)

    def test_http_redirect(self):
        ok, _ = check_http_redirects_to_https(
            _result(301, {"location": "https://jteam.ru/"}),
            "https://jteam.ru",
        )
        self.assertTrue(ok)

    def test_debug_toolbar_blocked(self):
        ok, _ = check_debug_toolbar(_result(404))
        self.assertTrue(ok)
        ok, _ = check_debug_toolbar(
            _result(200, body="<div id='djdt'></div>")
        )
        self.assertFalse(ok)

    def test_traceback_detected(self):
        ok, _ = check_debug_false(
            _result(500, body="Traceback (most recent call last)")
        )
        self.assertFalse(ok)
        ok, _ = check_debug_false(_result(404, body="Не найдено"))
        self.assertTrue(ok)

    def test_csrf_and_secure_cookie(self):
        ok, _ = check_csrf_on_login(
            _result(200, body='<input name="csrfmiddlewaretoken" value="x">')
        )
        self.assertTrue(ok)
        ok, _ = check_secure_cookies(
            _result(200, {"set-cookie": "csrftoken=abc; Secure; HttpOnly"})
        )
        self.assertTrue(ok)

    def test_hashed_static(self):
        ok, _ = check_hashed_static(
            _result(200, body='<link href="/static/css/base.0123456789ab.css">')
        )
        self.assertTrue(ok)

    def test_run_checks_all_pass(self):
        def fake_fetch(url, follow=True, timeout=20, insecure=False):
            if url.startswith("http://"):
                return _result(301, {"location": "https://jteam.ru/"}, url=url)
            if "/__debug__/" in url:
                return _result(404, url=url)
            if "/__prod_smoke_missing__/" in url:
                return _result(404, body="Not found", url=url)
            if "/login/" in url:
                return _result(
                    200,
                    {"set-cookie": "csrftoken=x; Secure"},
                    '<input name="csrfmiddlewaretoken" value="t">',
                    url,
                )
            return _result(
                200,
                {"strict-transport-security": "max-age=31536000"},
                '<link href="/static/css/base.0123456789ab.css">',
                url,
            )

        results = run_checks(
            base_url="https://jteam.ru",
            timeout=5,
            insecure=False,
            fetch_fn=fake_fetch,
        )
        failed = [name for name, ok, _ in results if not ok]
        self.assertEqual(failed, [])
