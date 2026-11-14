"""Historico de alteracoes (data/historico.json), compartilhado com 09-Otimizar.ps1."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

HIST_PATH = Path(__file__).resolve().parent.parent / "data" / "historico.json"
_LOCK = threading.RLock()  # serializa ler-modificar-gravar entre threads do painel


class History:
    def __init__(self, path: Path = HIST_PATH):
        self.path = Path(path)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        raw = self.path.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]

    def save(self, entries: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, tipo: str, alvo: str, antes: str, depois: str, reverter: list[str], resultado: str) -> dict:
        with _LOCK:
            return self._add(tipo, alvo, antes, depois, reverter, resultado)

    def _add(self, tipo: str, alvo: str, antes: str, depois: str, reverter: list[str], resultado: str) -> dict:
        entries = self.load()
        e = {"id": max([int(x.get("id", 0)) for x in entries] or [0]) + 1,
             "timestamp": datetime.now().isoformat(timespec="seconds"), "origem": "app",
             "tipo": tipo, "alvo": alvo, "antes": antes, "depois": depois,
             "reverter": reverter, "resultado": resultado, "revertido": False}
        entries.append(e)
        self.save(entries)
        return e

    def mark_reverted(self, entry_id: int, resultado: str) -> None:
        with _LOCK:
            self._mark_reverted(entry_id, resultado)

    def _mark_reverted(self, entry_id: int, resultado: str) -> None:
        entries = self.load()
        for e in entries:
            if int(e.get("id", 0)) == entry_id:
                e["revertido"] = True
                e["resultado_reversao"] = resultado
                e["revertido_em"] = datetime.now().isoformat(timespec="seconds")
        self.save(entries)
