"""Parseo de objetivos y catálogo de plataformas públicas conocidas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


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
    check_url_template: str | None = None
    check_accept: str | None = None
    query_user_param: str | None = None
    empty_json_array_means_missing: bool = False

    def profile_url(self, username: str) -> str:
        return self.url_template.format(username=username.lstrip("@"))

    def check_url(self, username: str) -> str:
        template = self.check_url_template or self.url_template
        return template.format(username=username.lstrip("@"))


PLATFORM_CATALOG: tuple[Platform, ...] = (
    Platform(
        key="github",
        label="GitHub",
        url_template="https://github.com/{username}",
        check_url_template="https://api.github.com/users/{username}",
        check_accept="application/vnd.github+json",
        hosts=("github.com", "www.github.com", "api.github.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/?$", r"^/users/(?P<user>[A-Za-z0-9-]+)/?$"),
        not_found_markers=("This is not the web page you are looking for", '"Not Found"'),
    ),
    Platform(
        key="gitlab",
        label="GitLab",
        url_template="https://gitlab.com/{username}",
        check_url_template="https://gitlab.com/api/v4/users?username={username}",
        check_accept="application/json",
        hosts=("gitlab.com", "www.gitlab.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._-]+)/?$",),
        empty_json_array_means_missing=True,
    ),
    Platform(
        key="bitbucket",
        label="Bitbucket",
        url_template="https://bitbucket.org/{username}/",
        hosts=("bitbucket.org", "www.bitbucket.org"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("Repository not found", "That page doesn't exist"),
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
        key="threads",
        label="Threads",
        url_template="https://www.threads.net/@{username}",
        hosts=("threads.net", "www.threads.net"),
        path_patterns=(r"^/@(?P<user>[A-Za-z0-9._]+)/?$",),
    ),
    Platform(
        key="youtube",
        label="YouTube",
        url_template="https://www.youtube.com/@{username}",
        hosts=("youtube.com", "www.youtube.com", "m.youtube.com"),
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
        check_url_template="https://www.reddit.com/user/{username}/about.json",
        check_accept="application/json",
        hosts=("reddit.com", "www.reddit.com", "old.reddit.com"),
        path_patterns=(
            r"^/user/(?P<user>[A-Za-z0-9_-]+)/?$",
            r"^/u/(?P<user>[A-Za-z0-9_-]+)/?$",
        ),
        not_found_markers=("Sorry, nobody on Reddit goes by that name", "page not found"),
    ),
    Platform(
        key="twitch",
        label="Twitch",
        url_template="https://www.twitch.tv/{username}",
        hosts=("twitch.tv", "www.twitch.tv"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_]{4,25})/?$",),
        not_found_markers=("Sorry. Unless you've got a time machine", "content unavailable"),
    ),
    Platform(
        key="pinterest",
        label="Pinterest",
        url_template="https://www.pinterest.com/{username}/",
        hosts=("pinterest.com", "www.pinterest.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._]+)/?$",),
        not_found_markers=("Sorry, we couldn't find that page", "User not found"),
    ),
    Platform(
        key="spotify",
        label="Spotify",
        url_template="https://open.spotify.com/user/{username}",
        hosts=("open.spotify.com", "spotify.com"),
        path_patterns=(r"^/user/(?P<user>[A-Za-z0-9._]+)/?$",),
        not_found_markers=("Couldn't find that user", "Page not found"),
    ),
    Platform(
        key="steam",
        label="Steam",
        url_template="https://steamcommunity.com/id/{username}",
        hosts=("steamcommunity.com", "www.steamcommunity.com"),
        path_patterns=(
            r"^/id/(?P<user>[A-Za-z0-9_-]+)/?$",
            r"^/profiles/(?P<user>\d+)/?$",
        ),
        not_found_markers=("The specified profile could not be found", "profile could not be found"),
    ),
    Platform(
        key="vimeo",
        label="Vimeo",
        url_template="https://vimeo.com/{username}",
        hosts=("vimeo.com", "www.vimeo.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("Sorry, we couldn't find that page", "Page not found"),
    ),
    Platform(
        key="medium",
        label="Medium",
        url_template="https://medium.com/@{username}",
        hosts=("medium.com", "www.medium.com"),
        path_patterns=(r"^/@(?P<user>[A-Za-z0-9._]+)/?$",),
        not_found_markers=("Out of nothing, something", "page not found"),
    ),
    Platform(
        key="patreon",
        label="Patreon",
        url_template="https://www.patreon.com/{username}",
        hosts=("patreon.com", "www.patreon.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("Sorry, this page isn't available", "page not found"),
    ),
    Platform(
        key="blogger",
        label="Blogger",
        url_template="https://{username}.blogspot.com",
        hosts=("blogspot.com", "www.blogspot.com", "blogger.com", "www.blogger.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("Blog not found", "Sorry, the blog you were looking for does not exist"),
    ),
    Platform(
        key="telegram",
        label="Telegram",
        url_template="https://t.me/{username}",
        hosts=("t.me", "telegram.me", "web.telegram.org"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_]{5,32})/?$",),
        not_found_markers=("If you have Telegram, you can contact",),
    ),
    Platform(
        key="linkedin",
        label="LinkedIn",
        url_template="https://www.linkedin.com/in/{username}/",
        hosts=("linkedin.com", "www.linkedin.com"),
        path_patterns=(r"^/in/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("This page doesn’t exist", "Page not found"),
    ),
    Platform(
        key="tumblr",
        label="Tumblr",
        url_template="https://{username}.tumblr.com",
        hosts=("tumblr.com", "www.tumblr.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("There's nothing here", "not found"),
    ),
    Platform(
        key="soundcloud",
        label="SoundCloud",
        url_template="https://soundcloud.com/{username}",
        hosts=("soundcloud.com", "www.soundcloud.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("We can't find that user", "404"),
    ),
    Platform(
        key="deviantart",
        label="DeviantArt",
        url_template="https://www.deviantart.com/{username}",
        hosts=("deviantart.com", "www.deviantart.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("doesn't exist", "Page not found"),
    ),
    Platform(
        key="flickr",
        label="Flickr",
        url_template="https://www.flickr.com/people/{username}/",
        hosts=("flickr.com", "www.flickr.com"),
        path_patterns=(
            r"^/people/(?P<user>[A-Za-z0-9@._-]+)/?$",
            r"^/photos/(?P<user>[A-Za-z0-9@._-]+)/?$",
        ),
        not_found_markers=("Page Not Found", "This member is no longer active"),
    ),
    Platform(
        key="behance",
        label="Behance",
        url_template="https://www.behance.net/{username}",
        hosts=("behance.net", "www.behance.net"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("Oops! We can’t find that page", "Page not found"),
    ),
    Platform(
        key="dribbble",
        label="Dribbble",
        url_template="https://dribbble.com/{username}",
        hosts=("dribbble.com", "www.dribbble.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("Whoops, that page is gone", "Page not found"),
    ),
    Platform(
        key="keybase",
        label="Keybase",
        url_template="https://keybase.io/{username}",
        hosts=("keybase.io", "www.keybase.io"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("User not found", "404"),
    ),
    Platform(
        key="aboutme",
        label="About.me",
        url_template="https://about.me/{username}",
        hosts=("about.me", "www.about.me"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("This page doesn't exist", "page not found"),
    ),
    Platform(
        key="linktree",
        label="Linktree",
        url_template="https://linktr.ee/{username}",
        hosts=("linktr.ee", "www.linktr.ee"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("The page you’re looking for doesn’t exist", "page not found"),
    ),
    Platform(
        key="vk",
        label="VK",
        url_template="https://vk.com/{username}",
        hosts=("vk.com", "www.vk.com", "m.vk.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9._]+)/?$",),
        not_found_markers=("Profile not found", "This page isn't available"),
    ),
    Platform(
        key="replit",
        label="Replit",
        url_template="https://replit.com/@{username}",
        hosts=("replit.com", "www.replit.com", "repl.it"),
        path_patterns=(r"^/@(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("404", "not found"),
    ),
    Platform(
        key="kaggle",
        label="Kaggle",
        url_template="https://www.kaggle.com/{username}",
        hosts=("kaggle.com", "www.kaggle.com"),
        path_patterns=(r"^/(?P<user>[A-Za-z0-9_-]+)/?$",),
        not_found_markers=("We can't find that page", "404-page"),
    ),
    Platform(
        key="hackernews",
        label="Hacker News",
        url_template="https://news.ycombinator.com/user?id={username}",
        hosts=("news.ycombinator.com",),
        path_patterns=(r"^/user/?$",),
        query_user_param="id",
        not_found_markers=("No such user",),
    ),
    Platform(
        key="snapchat",
        label="Snapchat",
        url_template="https://www.snapchat.com/add/{username}",
        hosts=("snapchat.com", "www.snapchat.com"),
        path_patterns=(r"^/add/(?P<user>[A-Za-z0-9._-]+)/?$",),
        not_found_markers=("Sorry! This user doesn't exist", "page not found"),
    ),
)

_HOST_INDEX = {host: platform for platform in PLATFORM_CATALOG for host in platform.hosts}


def lookup_platform(host: str) -> Platform | None:
    value = host.lower()
    if value in _HOST_INDEX:
        return _HOST_INDEX[value]
    if value.endswith(".blogspot.com") and value not in {"blogspot.com", "www.blogspot.com"}:
        return platform_by_key("blogger")
    if value.endswith(".tumblr.com") and value not in {"tumblr.com", "www.tumblr.com"}:
        return platform_by_key("tumblr")
    return None


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
    if host.endswith(".blogspot.com") and host.split(".")[0] not in {"www"}:
        candidate = host.split(".")[0]
        return candidate if USERNAME_RE.match(candidate) else None
    if host.endswith(".tumblr.com") and host.split(".")[0] not in {"www"}:
        candidate = host.split(".")[0]
        return candidate if USERNAME_RE.match(candidate) else None

    platform = lookup_platform(host)
    if platform is None:
        handle = value.rstrip("/").split("/")[-1].lstrip("@")
        return handle if USERNAME_RE.match(handle) else None

    if platform.query_user_param:
        params = parse_qs(parsed.query)
        values = params.get(platform.query_user_param, [])
        if values and USERNAME_RE.match(values[0]):
            return values[0]

    path = parsed.path or "/"
    for pattern in platform.path_patterns:
        match = re.match(pattern, path)
        if match and "user" in match.groupdict():
            return match.group("user")

    parts = [part for part in path.split("/") if part and part not in {"@", "user", "u", "c", "in", "id", "people", "photos", "add", "users"}]
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
        platform = lookup_platform(urlparse(value).netloc.lower())
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
    platform = lookup_platform(parsed.netloc.lower())
    if not platform:
        return None
    username = extract_username(url)
    if not username:
        return None
    return platform, username
