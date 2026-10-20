"""Motor recursivo de descubrimiento OSINT con peticiones resilientes."""

from __future__ import annotations

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


USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.6668.70 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.6613.146 Mobile Safari/537.36",
)

BLOCK_STATUSES = {401, 403, 429, 503}
CAPTCHA_MARKERS = (
    "cf-challenge",
    "cf-turnstile",
    "just a moment",
    "attention required",
    "captcha",
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
GENERIC_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
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
        min_delay: float = 1.5,
        max_delay: float = 4.0,
        timeout: float = 15.0,
    ) -> None:
        self.store = store
        self.console = console or Console()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.visited: set[str] = set()
        self.root_nodes: list[Node] = []
        self._cookies = httpx.Cookies()
        self._tree = Tree("[bold cyan]SpiderNet[/bold cyan]")
        self._branches: dict[str, Tree] = {}
        self._live_callback: Callable[[Tree], None] | None = None

    def attach_live(self, callback: Callable[[Tree], None]) -> None:
        self._live_callback = callback

    def crawl(self, username: str, max_depth: int) -> list[Node]:
        handle = username.lstrip("@")
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

        url = platform.profile_url(handle)
        status, detail, html = self._safe_get(url, platform)
        node = Node(
            platform=platform.key,
            username=handle,
            url=url,
            status=status,
            depth=depth,
            parent=parent,
            detail=detail,
            html=html if status == "found" else "",
        )
        self._persist(node)
        self._attach_to_tree(node)
        return node

    def _expand(self, node: Node, max_depth: int) -> None:
        if node.depth >= max_depth or node.status != "found":
            return

        html = node.html
        if not html:
            _, _, html = self._safe_get(node.url, platform_by_key(node.platform))
            node.html = html
        if not html:
            return

        for platform, username in self._extract_leads(html, node.url):
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
        self._polite_delay()
        try:
            with httpx.Client(
                headers=self._headers(),
                cookies=self._cookies,
                follow_redirects=True,
                timeout=self.timeout,
            ) as client:
                response = client.get(url)
                self._cookies.update(client.cookies)
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
        lowered = body.lower()
        return any(marker.lower() in lowered for marker in platform.not_found_markers)

    def _looks_like_challenge(self, body: str) -> bool:
        lowered = body.lower()
        return any(marker in lowered for marker in CAPTCHA_MARKERS)

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def _polite_delay(self) -> None:
        time.sleep(random.uniform(self.min_delay, self.max_delay))

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
