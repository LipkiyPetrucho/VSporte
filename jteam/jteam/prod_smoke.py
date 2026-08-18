"""Автоматические проверки P2 для https://jteam.ru (остальное — в PROD_CHECKLIST.md)."""

from __future__ import annotations

import argparse
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://jteam.ru"
HASHED_STATIC = re.compile(
    r"""/static/[^'"\s>]+\.[0-9a-f]{12}\.(?:css|js)""",
    re.IGNORECASE,
)
TRACEBACK_MARKERS = (
    "Traceback (most recent call last)",
    "DJANGO_SETTINGS_MODULE",
    "You’re seeing this error because you have",
    "You're seeing this error because you have",
    "Django tried these URL patterns",
)


@dataclass
class FetchResult:
    status: int
    headers: dict[str, str]
    body: str
    url: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _header_map(headers) -> dict[str, str]:
    if headers is None:
        return {}
    return {str(k).lower(): str(v) for k, v in headers.items()}


def fetch(
    url: str,
    *,
    follow: bool = True,
    timeout: int = 20,
    insecure: bool = False,
) -> FetchResult:
    handlers: list = []
    if not follow:
        handlers.append(_NoRedirect())
    context = ssl._create_unverified_context() if insecure else None
    https_handler = urllib.request.HTTPSHandler(context=context)
    handlers.append(https_handler)
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "JTeam-prod-smoke/1.0"},
    )
    try:
        with opener.open(request, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return FetchResult(resp.status, _header_map(resp.headers), body, url)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return FetchResult(exc.code, _header_map(exc.headers), body, url)


def _cookie_header(headers: dict[str, str]) -> str:
    parts = []
    for key, value in headers.items():
        if key == "set-cookie":
            parts.append(value)
    return "\n".join(parts)


def check_https_home(result: FetchResult) -> tuple[bool, str]:
    if result.status != 200:
        return False, f"GET / → {result.status}, ожидался 200"
    return True, "HTTPS / отвечает 200"


def check_http_redirects_to_https(
    result: FetchResult, https_origin: str
) -> tuple[bool, str]:
    if result.status not in (301, 302, 303, 307, 308):
        return False, f"HTTP / → {result.status}, ожидался редирект на HTTPS"
    location = result.headers.get("location", "")
    if not location.startswith("https://"):
        return False, f"Location не HTTPS: {location!r}"
    host = https_origin.split("://", 1)[-1].rstrip("/")
    if host not in location:
        return False, f"Location не на {https_origin}: {location!r}"
    return True, f"HTTP редиректит на {location}"


def check_debug_toolbar(result: FetchResult) -> tuple[bool, str]:
    if result.status == 404:
        return True, "__debug__/ недоступен (404)"
    if result.status == 200 and "djdt" in result.body.lower():
        return False, "__debug__/ открывается — debug toolbar в проде"
    if result.status in (301, 302):
        location = result.headers.get("location", "")
        if "/__debug__/" in location:
            return False, f"__debug__/ редиректит внутрь себя: {location}"
    return True, f"__debug__/ не отдаёт toolbar (status {result.status})"


def check_debug_false(result: FetchResult) -> tuple[bool, str]:
    for marker in TRACEBACK_MARKERS:
        if marker in result.body:
            return False, f"404-страница содержит признак DEBUG: {marker!r}"
    if result.status == 200:
        return False, "служебный 404-URL неожиданно вернул 200"
    return True, f"DEBUG выключен (404 без traceback, status {result.status})"


def check_csrf_on_login(result: FetchResult) -> tuple[bool, str]:
    if result.status != 200:
        return False, f"GET /login/ → {result.status}"
    if "csrfmiddlewaretoken" not in result.body:
        return False, "на /login/ нет csrfmiddlewaretoken"
    return True, "форма логина содержит CSRF-токен"


def check_secure_cookies(result: FetchResult) -> tuple[bool, str]:
    cookies = _cookie_header(result.headers)
    if not cookies:
        return False, "нет Set-Cookie на /login/ — проверьте Secure вручную в DevTools"
    if "secure" not in cookies.lower():
        return False, f"Set-Cookie без Secure: {cookies[:180]}"
    return True, "Set-Cookie содержит Secure"


def check_hsts(result: FetchResult) -> tuple[bool, str]:
    hsts = result.headers.get("strict-transport-security", "")
    if not hsts:
        return False, "нет заголовка Strict-Transport-Security"
    return True, f"HSTS: {hsts}"


def check_hashed_static(home: FetchResult) -> tuple[bool, str]:
    if HASHED_STATIC.search(home.body):
        return True, "в HTML есть hashed static (ManifestStaticFilesStorage)"
    if "/static/" in home.body:
        return False, "есть /static/, но без hash Manifest — collectstatic/storage?"
    return False, "в HTML главной нет ссылок /static/"


def run_checks(
    *,
    base_url: str,
    timeout: int,
    insecure: bool,
    fetch_fn=fetch,
) -> list[tuple[str, bool, str]]:
    https = base_url.rstrip("/")
    if https.startswith("http://"):
        https = "https://" + https[len("http://") :]
    elif not https.startswith("https://"):
        https = "https://" + https
    http = "http://" + https[len("https://") :]

    home = fetch_fn(https + "/", follow=True, timeout=timeout, insecure=insecure)
    http_home = fetch_fn(
        http + "/", follow=False, timeout=timeout, insecure=insecure
    )
    debug = fetch_fn(
        https + "/__debug__/", follow=False, timeout=timeout, insecure=insecure
    )
    missing = fetch_fn(
        https + "/__prod_smoke_missing__/",
        follow=True,
        timeout=timeout,
        insecure=insecure,
    )
    login = fetch_fn(
        https + "/login/", follow=True, timeout=timeout, insecure=insecure
    )

    return [
        ("https_home", *check_https_home(home)),
        ("http_redirect", *check_http_redirects_to_https(http_home, https)),
        ("debug_toolbar", *check_debug_toolbar(debug)),
        ("debug_false", *check_debug_false(missing)),
        ("csrf_login", *check_csrf_on_login(login)),
        ("secure_cookies", *check_secure_cookies(login)),
        ("hsts", *check_hsts(home)),
        ("hashed_static", *check_hashed_static(home)),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JTeam prod smoke (P2, automated)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="не проверять TLS-сертификат (только для staging)",
    )
    args = parser.parse_args(argv)

    print(f"Smoke: {args.base_url}")
    results = run_checks(
        base_url=args.base_url,
        timeout=args.timeout,
        insecure=args.insecure,
    )
    failed = 0
    for name, ok, message in results:
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {name}: {message}")
        if not ok:
            failed += 1
    print(
        "Готово."
        if failed == 0
        else f"Провалено проверок: {failed}. Ручные пункты — PROD_CHECKLIST.md"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
