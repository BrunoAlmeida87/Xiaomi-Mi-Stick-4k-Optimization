"""Cliente ADB minimalista para o Xiaomi TV Manager (sem dependencias externas)."""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

KEYCODES = {
    "UP": 19, "DOWN": 20, "LEFT": 21, "RIGHT": 22, "OK": 23, "ENTER": 66,
    "BACK": 4, "HOME": 3, "MENU": 82, "RECENTS": 187, "SETTINGS": 176,
    "PLAYPAUSE": 85, "PLAY": 126, "PAUSE": 127, "STOP": 86, "NEXT": 87, "PREV": 88,
    "FF": 90, "REW": 89, "VOLUP": 24, "VOLDOWN": 25, "MUTE": 164,
    "POWER": 26, "SLEEP": 223, "WAKEUP": 224, "SEARCH": 84, "ASSIST": 231,
}


def find_tool(name: str, configured: str = "") -> str | None:
    """Localiza adb/scrcpy: config -> PATH -> pastas comuns do winget/SDK no Windows."""
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [local / "Microsoft" / "WinGet" / "Links" / f"{name}.exe",
                      local / "Android" / "Sdk" / "platform-tools" / f"{name}.exe"]
        winget = local / "Microsoft" / "WinGet" / "Packages"
        if winget.is_dir():
            pattern = "Google.PlatformTools*" if name == "adb" else "Genymobile.scrcpy*"
            for pkg in winget.glob(pattern):
                candidates += list(pkg.rglob(f"{name}.exe"))
        for c in candidates:
            if c.is_file():
                return str(c)
    return None


@dataclass
class AdbResult:
    rc: int
    out: str
    err: str

    @property
    def text(self) -> str:
        return (self.out + ("\n" + self.err if self.err.strip() else "")).strip()

    @property
    def ok(self) -> bool:
        return self.rc == 0


class AdbClient:
    def __init__(self, adb_path: str, serial: str = ""):
        self.adb = adb_path
        self.serial = serial
        self._key_proc: subprocess.Popen | None = None
        self._key_lock = threading.Lock()

    # ---------- execucao basica ----------
    def run(self, *args: str, timeout: float = 20, use_serial: bool = True) -> AdbResult:
        cmd = [self.adb]
        if use_serial and self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=timeout,
                               creationflags=CREATE_NO_WINDOW)
            dec = lambda b: b.decode("utf-8", errors="replace").replace("\r\n", "\n")
            return AdbResult(p.returncode, dec(p.stdout), dec(p.stderr))
        except subprocess.TimeoutExpired:
            return AdbResult(124, "", f"tempo esgotado ({timeout}s): {' '.join(args)}")
        except OSError as e:
            return AdbResult(127, "", f"falha ao executar adb: {e}")

    def shell(self, command: str, timeout: float = 20) -> AdbResult:
        return self.run("shell", command, timeout=timeout)

    # ---------- conexao ----------
    def connect(self, ip: str, port: int = 5555) -> AdbResult:
        self.serial = f"{ip}:{port}"
        self.run("start-server", use_serial=False, timeout=15)
        return self.run("connect", self.serial, use_serial=False, timeout=15)

    def pair(self, host_port: str, code: str) -> AdbResult:
        return self.run("pair", host_port, code, use_serial=False, timeout=30)

    def disconnect(self) -> AdbResult:
        self.close_key_shell()
        if not self.serial:
            return AdbResult(0, "", "")
        return self.run("disconnect", self.serial, use_serial=False, timeout=10)

    def state(self) -> str:
        if not self.serial:
            return "sem IP"
        r = self.run("get-state", timeout=8)
        s = r.out.strip()
        if s in ("device", "offline", "unauthorized", "recovery", "bootloader"):
            return s
        if "unauthorized" in r.err:
            return "unauthorized"
        if "offline" in r.err:
            return "offline"
        return "desconectado"

    def devices(self) -> str:
        return self.run("devices", "-l", use_serial=False).text

    def getprop(self, key: str) -> str:
        return self.shell(f"getprop {key}").out.strip()

    # ---------- teclas (shell persistente = menor latencia) ----------
    def _ensure_key_shell(self) -> subprocess.Popen:
        if self._key_proc is None or self._key_proc.poll() is not None:
            self._key_proc = subprocess.Popen(
                [self.adb, "-s", self.serial, "shell"], stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW)
        return self._key_proc

    def send_shell_line(self, line: str) -> bool:
        with self._key_lock:
            for _ in range(2):
                try:
                    proc = self._ensure_key_shell()
                    assert proc.stdin is not None
                    proc.stdin.write((line + "\n").encode())
                    proc.stdin.flush()
                    return True
                except (OSError, BrokenPipeError, AssertionError):
                    self._key_proc = None
            # fallback: comando avulso
            return self.shell(line).ok

    def key(self, name_or_code) -> bool:
        code = KEYCODES.get(str(name_or_code).upper(), name_or_code)
        return self.send_shell_line(f"input keyevent {int(code)}")

    def text(self, value: str) -> bool:
        return self.send_shell_line(f"input text {escape_input_text(value)}")

    def close_key_shell(self) -> None:
        with self._key_lock:
            if self._key_proc and self._key_proc.poll() is None:
                try:
                    self._key_proc.stdin.close()  # type: ignore[union-attr]
                    self._key_proc.wait(timeout=2)  # deixa os ultimos comandos chegarem
                except (OSError, subprocess.TimeoutExpired):
                    self._key_proc.terminate()
            self._key_proc = None

    # ---------- apps ----------
    def launch(self, package: str) -> AdbResult:
        if not is_valid_package(package):
            return AdbResult(2, "", f"nome de pacote invalido: {package}")
        r = self.shell(f"monkey -p {package} -c android.intent.category.LEANBACK_LAUNCHER 1")
        if "No activities found" in r.text or "aborted" in r.text:
            r = self.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
        return r

    def force_stop(self, package: str) -> AdbResult:
        if not is_valid_package(package):
            return AdbResult(2, "", f"nome de pacote invalido: {package}")
        return self.shell(f"am force-stop {package}")


def is_valid_package(name: str) -> bool:
    import re
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+", name or ""))


def escape_input_text(value: str) -> str:
    """Escapa texto para 'input text' (espaco -> %s, metacaracteres do shell com \\)."""
    out = []
    for ch in value:
        if ch == " ":
            out.append("%s")
        elif ch in "\\\"'`$&|;<>()*?!#~[]{}%":
            out.append("\\" + ch)
        elif ord(ch) < 32:
            continue
        else:
            out.append(ch)
    return "".join(out)
