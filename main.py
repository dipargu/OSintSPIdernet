#!/usr/bin/env python3
"""CLI de SpiderNet V2: descubrimiento OSINT de perfiles públicos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt

from core.logger import ResultsStore
from core.spider import SpiderNet
from modules.platform_check import PLATFORM_CATALOG, parse_target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SpiderNet V2 — enumeración OSINT de perfiles públicos",
    )
    parser.add_argument("target", nargs="?", help="Username o URL de perfil")
    parser.add_argument(
        "-d",
        "--max-depth",
        type=int,
        default=None,
        help="Profundidad máxima de recursión (0 = solo chequeo inicial)",
    )
    return parser


def ask_inputs(console: Console, args: argparse.Namespace) -> tuple[str, int]:
    target = args.target or Prompt.ask("[bold]Objetivo[/bold] (username o URL)")
    if args.max_depth is None:
        max_depth = IntPrompt.ask("[bold]Límite de profundidad[/bold]", default=1)
    else:
        max_depth = args.max_depth
    if max_depth < 0:
        console.print("[red]La profundidad no puede ser negativa.[/red]")
        sys.exit(1)
    return target.strip(), max_depth


def main() -> int:
    console = Console()
    args = build_parser().parse_args()
    raw_target, max_depth = ask_inputs(console, args)

    parsed = parse_target(raw_target)
    username = parsed["username"]
    if not username:
        console.print(
            "[red]No pude extraer un username válido. "
            "Usa un handle (ej. dipargu) o una URL de perfil.[/red]"
        )
        return 1

    console.print(
        Panel.fit(
            f"[bold]Objetivo:[/bold] {raw_target}\n"
            f"[bold]Username:[/bold] {username}\n"
            f"[bold]Plataforma origen:[/bold] {parsed['source_platform'] or 'n/a'}\n"
            f"[bold]max_depth:[/bold] {max_depth}\n"
            f"[bold]Plataformas:[/bold] {len(PLATFORM_CATALOG)}\n"
            f"[bold]Log:[/bold] {Path('logs/results.json').resolve()}",
            title="SpiderNet V2",
            border_style="cyan",
        )
    )

    store = ResultsStore()
    store.start_run(raw_target, username, max_depth)
    spider = SpiderNet(store=store, console=console)

    try:
        with Live(spider.tree, console=console, refresh_per_second=8) as live:
            spider.attach_live(live.update)
            spider.crawl(username, max_depth)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrumpido. Los hallazgos ya están en logs/results.json.[/yellow]")
        return 130

    found = [n for n in store.snapshot()["nodes"] if n["status"] == "found"]
    blocked = [n for n in store.snapshot()["nodes"] if n["status"] == "blocked"]
    console.print(
        f"\n[green]Perfiles confirmados:[/green] {len(found)}  "
        f"[red]Bloqueados:[/red] {len(blocked)}  "
        f"[dim]Total nodos:[/dim] {len(store.snapshot()['nodes'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
