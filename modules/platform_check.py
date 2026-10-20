"""Parseo de objetivos y catálogo de plataformas públicas conocidas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,39}$")


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    url_template: str
    path_patterns: tuple[str, ...]
    hosts: tuple[str, ...]
    not_found_markers: tuple[str, ...] = ()
    found_markers: tuple[str, ...] = ()

    def profile_url(self, username: str) -> str:
        handle = username.lstrip("@")
        return self.url_template.format(username=handle)


PLATFORM_CATALOG: tuple[Platform, ...] = (
    Platform(
        key="github",
        label="GitHub",
        url_template="https://github.com/{username}",
        hosts=("github.com", "www.github.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/?$",),
        not_found_markers=("This is not the web page you are looking for", "Not Found"),
    ),
    Platform(
        key="tiktok",
        label="TikTok",
        url_template="https://www.tiktok.com/@{username}",
        hosts=("tiktok.com", "www.tiktok.com", "vm.tiktok.com"),
        path_patterns=(r"^/@(?P<user>[A-Za-z0-9._]+)/?$",),
        not_found_markers=("Couldn't find this account", "No se pudo encontrar esta cuenta"),
    ),
    Platform(
        key="instagram",
        label="Instagram",
        url_template="https://www.instagram.com/{username}/",
        hosts=("instagram.com", "www.instagram.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._]+)/?$",),
        not_found_markers=("Sorry, this page isn't available", "esta página no está disponible"),
    ),
    Platform(
        key="youtube",
        label="YouTube",
        url_template="https://www.youtube.com/@{username}",
        hosts=("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"),
        path_patterns=(
            r"^/@(?P<user>[A-Za-z0-9._-]+)/?$",
            r"^/c/(?P<user>[A-Za-z0-9._-]+)/?$",
            r"^/user/(?P<user>[A-Za-z0-9._-]+)/?$",
        ),
        not_found_markers=("This page isn't available", "404 Not Found"),
    ),
    Platform(
        key="facebook",
        label="Facebook",
        url_template="https://www.facebook.com/{username}",
        hosts=("facebook.com", "www.facebook.com", "m.facebook.com", "fb.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9.]+)/?$",),
        not_found_markers=("This content isn't available", "Page Not Found"),
    ),
    Platform(
        key="x",
        label="X/Twitter",
        url_template="https://x.com/{username}",
        hosts=("x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_]{1,15})/?$",),
        not_found_markers=("This account doesn’t exist", "This account doesn't exist"),
    ),
    Platform(
        key="reddit",
        label="Reddit",
        url_template="https://www.reddit.com/user/{username}",
        hosts=("reddit.com", "www.reddit.com", "old.reddit.com"),
        path_patterns=(
            r"^/user/(?P<user>[A-Za-z0-9_-]+)/?$",
            r"^/u/(?P<user>[A-Za-z0-9_-]+)/?$",
        ),
        not_found_markers=("Sorry, nobody on Reddit goes by that name", "page not found"),
    ),
)

_HOST_INDEX = {host: platform for platform in PLATFORM_CATALOG for host in platform.hosts}


def normalize_host(host: str) -> str:
    return host.lower().removeprefix("www.")


def extract_username(raw: str) -> str | None:
    """Extrae un handle de una URL de plataforma o valida un username plano."""
    value = raw.strip()
    if not value:
        return None

    if not re.match(r"^https?://", value, flags=re.IGNORECASE):
        handle = value.lstrip("@")
        return handle if USERNAME_RE.match(handle) else None

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    platform = _HOST_INDEX.get(host)
    if platform is None:
        handle = value.rstrip("/").split("/")[-1].lstrip("@")
        return handle if USERNAME_RE.match(handle) else None

    path = parsed.path or "/"
    for pattern in platform.path_patterns:
        match = re.match(pattern, path)
        if match:
            return match.group("user")

    parts = [part for part in path.split("/") if part and part not in {"@", "user", "u", "c"}]
    if parts:
        candidate = parts[0].lstrip("@")
        if USERNAME_RE.match(candidate):
            return candidate
    return None


def parse_target(raw: str) -> dict[str, str | None]:
    """Devuelve el objetivo original, el username extraído y la plataforma de origen si aplica."""
    value = raw.strip()
    source_platform = None
    if re.match(r"^https?://", value, flags=re.IGNORECASE):
        parsed = urlparse(value)
        platform = _HOST_INDEX.get(parsed.netloc.lower())
        if platform:
            source_platform = platform.key
    username = extract_username(value)
    return {
        "target": value,
        "username": username,
        "source_platform": source_platform,
    }


def platform_by_key(key: str) -> Platform | None:
    for platform in PLATFORM_CATALOG:
        if platform.key == key:
            return platform
    return None


def detect_platform_from_url(url: str) -> tuple[Platform, str] | None:
    parsed = urlparse(url.strip())
    platform = _HOST_INDEX.get(parsed.netloc.lower())
    if not platform:
        return None
    username = extract_username(url)
    if not username:
        return None
    return platform, username
