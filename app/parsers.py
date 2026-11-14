"""Interpretacao das saidas de comandos ADB. Funcoes puras (testaveis sem dispositivo)."""
from __future__ import annotations

import re


def parse_meminfo(text: str) -> dict[str, int]:
    """/proc/meminfo -> {campo: kB}."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\w[\w()]*):\s+(\d+)\s*kB", line.strip())
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def parse_df(text: str) -> list[dict[str, str]]:
    """Saida de 'df' / 'df -h' (toybox) -> lista de {fs,size,used,avail,use,mount}."""
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[0] != "Filesystem" and parts[-1].startswith("/"):
            rows.append({"fs": parts[0], "size": parts[1], "used": parts[2],
                         "avail": parts[3], "use": parts[4], "mount": parts[5]})
    return rows


def parse_packages(text: str) -> list[str]:
    """'pm list packages' -> nomes ordenados (aceita tambem a forma -f: package:/path=nome)."""
    pkgs = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("package:"):
            continue
        body = line[len("package:"):]
        if "=" in body and body.startswith("/"):
            body = body.rsplit("=", 1)[1]
        pkgs.add(body.strip())
    return sorted(pkgs)


def parse_pss_by_process(text: str) -> dict[str, int]:
    """'dumpsys meminfo' -> {processo: kB}. Prefere 'Total PSS by process' (memoria real, sem contar em dobro
    a compartilhada); usa 'Total RSS by process' so quando o firmware nao traz PSS."""
    sections: dict[str, dict[str, int]] = {}
    cur: dict[str, int] | None = None
    for line in text.splitlines():
        h = re.match(r"^Total (PSS|RSS) by process", line.strip())
        if h:
            cur = sections.setdefault(h.group(1), {})
            continue
        if cur is None:
            continue
        m = re.match(r"^\s*([\d,]+)K:\s+(\S+)(?:\s+\(pid\s+\d+.*\))?", line)
        if m:
            name = m.group(2).split(":")[0]  # com.app:servico -> com.app
            cur[name] = cur.get(name, 0) + int(m.group(1).replace(",", ""))
        elif cur and (line.strip() == "" or not line.startswith(" ")):
            cur = None
    return sections.get("PSS") or sections.get("RSS") or {}


def parse_usagestats_last_used(text: str) -> dict[str, str]:
    """'dumpsys usagestats' -> {pacote: lastTimeUsed mais recente} (melhor esforco)."""
    out: dict[str, str] = {}
    for m in re.finditer(r'package=(\S+)[^\n]*?lastTimeUsed="([^"]+)"', text):
        pkg, ts = m.group(1), m.group(2)
        if ts.startswith("1970"):
            continue
        if ts > out.get(pkg, ""):
            out[pkg] = ts
    return out


def parse_activity_packages(text: str) -> list[str]:
    """Saida de 'cmd package resolve-activity/query-activities --brief' -> pacotes (pacote/atividade)."""
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Za-z][\w.]*)/\S+\s*$", line)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def home_guard(pkg: str, default_home_out: str, all_homes_out: str) -> str | None:
    """Motivo para RECUSAR desativar 'pkg' por ser a tela inicial, ou None se for seguro."""
    default = parse_activity_packages(default_home_out)
    if pkg in default:
        return f"{pkg} e a tela inicial PADRAO da TV. Desativar deixaria a TV sem tela inicial."
    homes = [h for h in parse_activity_packages(all_homes_out) if h not in ("com.android.tv.settings", "com.android.settings")]
    if pkg in homes and len(homes) <= 1:
        return f"{pkg} e a UNICA tela inicial instalada. Desativar deixaria a TV sem tela inicial."
    if not default and not homes:
        return "Nao foi possivel confirmar qual e a tela inicial; por seguranca, nada foi alterado."
    return None


def parse_bluetooth(text: str) -> dict:
    """'dumpsys bluetooth_manager' -> resumo (estado, nome, dispositivos pareados)."""
    info: dict = {"enabled": None, "state": None, "name": None, "bonded": []}
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^enabled:\s*(\w+)", s)
        if m and info["enabled"] is None:
            info["enabled"] = m.group(1).lower() == "true"
        m = re.match(r"^state:\s*(\S+)", s)
        if m and info["state"] is None:
            info["state"] = m.group(1)
        m = re.match(r"^name:\s*(.+)$", s)
        if m and info["name"] is None:
            info["name"] = m.group(1)
    sec = re.search(r"Bonded devices:\n((?:\s+.+\n?)+)", text)
    if sec:
        for line in sec.group(1).splitlines():
            m = re.match(r"\s+((?:[0-9A-Fa-fX]{2}:){5}[0-9A-Fa-fX]{2})\s*(?:\[[^\]]*\])?\s*(.*)$", line)
            if m:
                info["bonded"].append({"address": m.group(1), "name": m.group(2).strip()})
    return info


def parse_input_devices(text: str) -> list[dict[str, str]]:
    """'dumpsys input' -> dispositivos de entrada (o controle BT aparece aqui)."""
    buses = {"0x0005": "Bluetooth", "0x0003": "USB", "0x0019": "Virtual/host", "0x0000": "Interno"}
    devs: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    for line in text.splitlines():
        m = re.match(r"^\s*Device (-?\d+):\s*(.*)$", line)
        if m:
            cur = {"id": m.group(1), "name": m.group(2).strip(), "sources": "", "bus": ""}
            devs.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("Sources:") and not cur["sources"]:
            cur["sources"] = s.split(":", 1)[1].strip()
        elif s.startswith("Identifier:") and not cur["bus"]:
            bm = re.search(r"bus=(0x[0-9a-fA-F]+)", s)
            if bm:
                cur["bus"] = buses.get(bm.group(1).lower(), bm.group(1))
    return devs


def count_bt_disconnects(logcat: str) -> list[str]:
    pat = re.compile(r"disconnect|link.?loss|supervision.?timeout|connection.?timeout|hci.*(err|timeout)", re.I)
    bt = re.compile(r"bluetooth|bt_|bta_|btif|hid|gatt|l2cap|hci", re.I)
    return [l for l in logcat.splitlines() if pat.search(l) and bt.search(l)]


def kb_to_mb(kb: int | None) -> str:
    return "n/d" if kb is None else f"{kb / 1024:.0f} MB"
