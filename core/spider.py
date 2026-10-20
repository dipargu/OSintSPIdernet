"""Motor recursivo de descubrimiento OSINT con peticiones resilientes."""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.tree import Tree

from modules.platform_check import (
    PLATFORM_CATALOG,
    Platform,
    detect_platform_from_url,
    platform_by_key,
)

from .logger import ResultsStore


@dataclass(frozen=True)
class BrowserProfile:
    user_agent: str
    sec_ch_ua: str | None = None
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: str = '"Windows"'


BROWSER_PROFILES = (
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        sec_ch_ua_platform='"Windows"',
    ),
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        sec_ch_ua_platform='"macOS"',
    ),
    BrowserProfile(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    ),
    BrowserProfile(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
        sec_ch_ua_platform='"macOS"',
    ),
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_1) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.1 Safari/605.1.15"
        ),
        sec_ch_ua_platform='"macOS"',
    ),
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1"
        ),
        sec_ch_ua_mobile="?1",
        sec_ch_ua_platform='"iOS"',
    ),
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        sec_ch_ua_mobile="?1",
        sec_ch_ua_platform='"Android"',
    ),
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        ),
        sec_ch_ua='"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        sec_ch_ua_platform='"Windows"',
    ),
    BrowserProfile(
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.6723.107 Mobile Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        sec_ch_ua_mobile="?1",
        sec_ch_ua_platform='"Android"',
    ),
    BrowserProfile(
        user_agent="Mozilla/5.0 (Android 14; Mobile; rv:133.0) Gecko/133.0 Firefox/133.0",
        sec_ch_ua_mobile="?1",
        sec_ch_ua_platform='"Android"',
    ),
)

ACCEPT_LANGUAGES = (
    "en-US,en;q=0.9,es;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
    "en-GB,en;q=0.9,es;q=0.7",
    "en-US,en;q=0.8",
)

BLOCK_STATUSES = {401, 403, 429, 503}
CAPTCHA_MARKERS = (
    "cf-challenge",
    "cf-turnstile",
    "just a moment",
    "attention required",
    "hcaptcha",
    "recaptcha",
    "verify you are human",
)
RESERVED_HANDLES = {
    "about",
    "account",
    "accounts",
    "admin",
    "api",
    "c",
    "collections",
    "compose",
    "explore",
    "features",
    "hashtag",
    "home",
    "i",
    "intent",
    "issues",
    "joinchat",
    "login",
    "logout",
    "marketplace",
    "messages",
    "notifications",
    "orgs",
    "p",
    "pages",
    "privacy",
    "pulls",
    "reel",
    "reels",
    "search",
    "settings",
    "share",
    "signup",
    "sso",
    "stories",
    "tags",
    "topics",
    "user",
    "users",
    "watch",
    "help",
    "tos",
}
MENTION_RE = re.compile(r"(?<![\w/])@([A-Za-z0-9._-]{2,39})")
GENERIC_URL_RE = re.compile(r"https?://[^\s\"'<>\\]+", re.IGNORECASE)
TWITTER_FIELD_RE = re.compile(r'"twitter_username"\s*:\s*"([^"]+)"')
MAX_LEADS_PER_PAGE = 12


@dataclass
class Node:
    platform: str
    username: str
    url: str
    status: str
    depth: int
    parent: str | None = None
    detail: str = ""
    html: str = ""
    children: list["Node"] = field(default_factory=list)

    @property
    def identity(self) -> str:
        return f"{self.platform}:{self.username.lower()}"


class SpiderNet:
    def __init__(
        self,
        store: ResultsStore,
        console: Console | None = None,
        min_delay: float = 0.5,
        max_delay: float = 2.0,
        timeout: float = 15.0,
    ) -> None:
        self.store = store
        self.console = console or Console()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.visited: set[str] = set()
        self.root_nodes: list[Node] = []
        self._last_host: str | None = None
        self._client = httpx.Client(follow_redirects=True, timeout=self.timeout, http2=False)
        self._tree = Tree("[bold cyan]SpiderNet[/bold cyan]")
        self._branches: dict[str, Tree] = {}
        self._live_callback: Callable[[Tree], None] | None = None

    def attach_live(self, callback: Callable[[Tree], None]) -> None:
        self._live_callback = callback

    def close(self) -> None:
        self._client.close()

    def crawl(self, username: str, max_depth: int) -> list[Node]:
        handle = username.lstrip("@")
        try:
            roots = [
                node
                for platform in PLATFORM_CATALOG
                if (node := self._probe_platform(platform, handle, depth=0, parent=None))
            ]
            self.root_nodes = [node for node in roots if node.status == "found"]
            if max_depth > 0:
                for root in list(self.root_nodes):
                    self._expand(root, max_depth)
            return self.root_nodes
        finally:
            self.close()

    def _probe_platform(
        self,
        platform: Platform,
        username: str,
        depth: int,
        parent: str | None,
    ) -> Node | None:
        handle = username.lstrip("@")
        if handle.lower() in RESERVED_HANDLES:
            return None

        identity = f"{platform.key}:{handle.lower()}"
        if identity in self.visited:
            return None
        self.visited.add(identity)

        profile_url = platform.profile_url(handle)
        probe_url = platform.check_url(handle)
        status, detail, body = self._safe_get(probe_url, platform)
        node = Node(
            platform=platform.key,
            username=handle,
            url=profile_url,
            status=status,
            depth=depth,
            parent=parent,
            detail=detail,
            html=body if status == "found" else "",
        )
        self._persist(node)
        self._attach_to_tree(node)
        return node

    def _expand(self, node: Node, max_depth: int) -> None:
        if node.depth >= max_depth or node.status != "found":
            return

        body = node.html
        if not body:
            _, _, body = self._safe_get(node.url, platform_by_key(node.platform))
            node.html = body
        if not body:
            return

        for platform, username in self._extract_leads(body, node.url):
            child = self._probe_platform(platform, username, node.depth + 1, node.identity)
            if child is None:
                continue
            node.children.append(child)
            if child.status == "found":
                self._expand(child, max_depth)

    def _extract_leads(self, html: str, base_url: str) -> list[tuple[Platform, str]]:
        found: dict[str, tuple[Platform, str]] = {}
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        hrefs = [urljoin(base_url, tag.get("href", "")) for tag in soup.select("a[href]")]
        hrefs.extend(GENERIC_URL_RE.findall(html))

        twitter_match = TWITTER_FIELD_RE.search(html)
        if twitter_match:
            x_platform = platform_by_key("x")
            if x_platform:
                hrefs.append(x_platform.profile_url(twitter_match.group(1)))

        for href in hrefs:
            detected = detect_platform_from_url(href)
            if not detected:
                continue
            platform, username = detected
            if username.lower() in RESERVED_HANDLES:
                continue
            identity = f"{platform.key}:{username.lower()}"
            if identity not in self.visited:
                found[identity] = (platform, username)

        current = detect_platform_from_url(base_url)
        if current:
            page_text = soup.get_text(" ", strip=True)
            for mention in MENTION_RE.findall(page_text):
                if mention.lower() in RESERVED_HANDLES:
                    continue
                if mention.lower() == current[1].lower():
                    continue
                identity = f"{current[0].key}:{mention.lower()}"
                if identity not in self.visited:
                    found[identity] = (current[0], mention)

        return list(found.values())[:MAX_LEADS_PER_PAGE]

    def _safe_get(self, url: str, platform: Platform | None) -> tuple[str, str, str]:
        self._polite_delay(url)
        try:
            response = self._client.get(url, headers=self._headers(url, platform))
        except httpx.RequestError as exc:
            return "blocked", f"error de red: {exc.__class__.__name__}", ""
        except Exception as exc:  # noqa: BLE001 - el motor no debe caer nunca
            return "blocked", f"excepción: {exc.__class__.__name__}", ""

        body = response.text or ""
        if response.status_code in BLOCK_STATUSES or self._looks_like_challenge(body):
            return "blocked", f"HTTP {response.status_code}", ""
        if response.status_code in {404, 410}:
            return "not_found", f"HTTP {response.status_code}", ""
        if response.status_code >= 400:
            return "blocked", f"HTTP {response.status_code}", ""
        if platform and self._is_soft_404(body, platform):
            return "not_found", "soft-404", ""
        return "found", f"HTTP {response.status_code}", body

    def _is_soft_404(self, body: str, platform: Platform) -> bool:
        stripped = body.strip()
        if platform.empty_json_array_means_missing:
            try:
                parsed = json.loads(stripped)
                if parsed == []:
                    return True
            except json.JSONDecodeError:
                pass
        lowered = body.lower()
        return any(marker.lower() in lowered for marker in platform.not_found_markers)

    def _looks_like_challenge(self, body: str) -> bool:
        lowered = body.lower()
        return any(marker in lowered for marker in CAPTCHA_MARKERS)

    def _headers(self, url: str, platform: Platform | None) -> dict[str, str]:
        profile = random.choice(BROWSER_PROFILES)
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            "User-Agent": profile.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Referer": origin + "/",
        }
        if profile.sec_ch_ua:
            headers["sec-ch-ua"] = profile.sec_ch_ua
            headers["sec-ch-ua-mobile"] = profile.sec_ch_ua_mobile
            headers["sec-ch-ua-platform"] = profile.sec_ch_ua_platform
        if platform and platform.check_accept:
            headers["Accept"] = platform.check_accept
            headers["Sec-Fetch-Dest"] = "empty"
            headers["Sec-Fetch-Mode"] = "cors"
            headers["Sec-Fetch-Site"] = "same-site"
        if platform and platform.key == "github":
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        return headers

    def _polite_delay(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        if self._last_host is None:
            self._last_host = host
            return
        if host != self._last_host:
            time.sleep(random.uniform(self.min_delay, self.max_delay))
        else:
            time.sleep(random.uniform(0.25, min(self.max_delay, 0.8)))
        self._last_host = host

    def _persist(self, node: Node) -> None:
        self.store.add_node(
            {
                "platform": node.platform,
                "username": node.username,
                "url": node.url,
                "status": node.status,
                "depth": node.depth,
                "parent": node.parent,
                "detail": node.detail,
            }
        )

    def _attach_to_tree(self, node: Node) -> None:
        parent_tree = self._branches.get(node.parent) if node.parent else self._tree
        if parent_tree is None:
            parent_tree = self._tree
        branch = parent_tree.add(self._format_label(node))
        self._branches[node.identity] = branch
        if self._live_callback:
            self._live_callback(self._tree)

    def _format_label(self, node: Node) -> str:
        marker = {
            "found": "[green][OK][/green]",
            "not_found": "[dim][No existe][/dim]",
            "blocked": "[red][Fallido/Bloqueado][/red]",
        }.get(node.status, "[yellow][?][/yellow]")
        return f"{marker} {node.platform} / {node.username}  {node.url}"

    @property
    def tree(self) -> Tree:
        return self._tree
