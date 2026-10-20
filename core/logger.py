"""Persistencia inmediata de resultados y utilidades de logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
RESULTS_PATH = LOGS_DIR / "results.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResultsStore:
    """Guarda cada hallazgo en disco al instante para evitar pérdida de datos."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or RESULTS_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._data: dict[str, Any] = {
            "target": None,
            "username": None,
            "max_depth": None,
            "started_at": utc_now(),
            "updated_at": utc_now(),
            "nodes": [],
        }
        self._flush()

    def start_run(self, target: str, username: str, max_depth: int) -> None:
        with self._lock:
            self._data["target"] = target
            self._data["username"] = username
            self._data["max_depth"] = max_depth
            self._data["started_at"] = utc_now()
            self._data["updated_at"] = utc_now()
            self._data["nodes"] = []
            self._flush()

    def add_node(self, node: dict[str, Any]) -> dict[str, Any]:
        record = {**node, "timestamp": node.get("timestamp") or utc_now()}
        with self._lock:
            self._data["nodes"].append(record)
            self._data["updated_at"] = utc_now()
            self._flush()
        return record

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))

    def _flush(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)


class ContextLogger:
    """Actualiza context_log.md con el estado de implementación entre sesiones."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (PROJECT_ROOT / "context_log.md")

    def write(
        self,
        last_action: str,
        how: str,
        errors: str,
        next_steps: str,
    ) -> None:
        content = (
            "# SpiderNet V2 — Context Log\n\n"
            f"- **Última acción realizada:** {last_action}\n"
            f"- **Cómo se ha implementado:** {how}\n"
            f"- **Errores detectados/pendientes:** {errors}\n"
            f"- **Siguientes pasos recomendados:** {next_steps}\n"
            f"\n_Actualizado: {utc_now()}_\n"
        )
        self.path.write_text(content, encoding="utf-8")
