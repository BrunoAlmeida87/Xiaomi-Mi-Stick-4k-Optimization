"""Xiaomi TV Manager - painel local para controlar, diagnosticar e otimizar o Mi TV Stick via ADB.

Executar:  py -3 app\\xiaomi_tv_manager.py   (ou Iniciar-XiaomiTVManager.bat)
Somente biblioteca padrao do Python (Tkinter).
"""
from __future__ import annotations

import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adb_client import CREATE_NO_WINDOW, AdbClient, find_tool, is_valid_package  # noqa: E402
from history import History  # noqa: E402
from knowledge import ORDEM, KnowledgeBase  # noqa: E402
import parsers as P  # noqa: E402
import netdiag as N  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
REPORTS = ROOT / "reports"
APP_TITLE = "Xiaomi TV Manager"
ANIM_KEYS = ("window_animation_scale", "transition_animation_scale", "animator_duration_scale")

FILTROS = ["Pode desativar ou depende do uso", "Pode desativar se não usa", "Depende do seu uso", "Instalados por você",
           "Sem informação", "Necessários (manter)", "Desativados", "Todos"]
FILTRO_CATS = {FILTROS[0]: {"Candidato", "Opcional"}, FILTROS[1]: {"Candidato"}, FILTROS[2]: {"Opcional"},
               FILTROS[3]: {"Instalado por você"}, FILTROS[4]: {"Desconhecido"}, FILTROS[5]: {"Essencial"}}
CORES = {"Candidato": "#1b7f2a", "Opcional": "#b35c00", "Instalado por você": "#1f5fbf", "Desconhecido": "#b00020", "Essencial": "#666666"}

STREAMING_SHORTCUTS = {
    "Netflix": "com.netflix.ninja", "YouTube": "com.google.android.youtube.tv",
    "Prime Video": "com.amazon.amazonvideo.livingroom", "Disney+": "com.disney.disneyplus",
    "Max": "com.wbd.stream", "Globoplay": "com.globo.globotv", "Spotify": "com.spotify.tv.android",
    "Play Store": "com.android.vending", "Configuracoes": "com.android.tv.settings",
}

# Comandos SOMENTE LEITURA da coleta completa (mesma lista do 05-Diagnostico.ps1)
DIAG_COMMANDS = [
    ("01-getprop", "getprop"),
    ("02-meminfo", "cat /proc/meminfo"),
    ("03-dumpsys-meminfo", "dumpsys meminfo"),
    ("04-armazenamento", "df -h; echo; df"),
    ("05-cpuinfo", "cat /proc/cpuinfo"),
    ("06-top", "top -b -n 1 -m 30"),
    ("07-dumpsys-cpuinfo", "dumpsys cpuinfo"),
    ("08-uptime-load", "uptime; cat /proc/loadavg"),
    ("09-servicos-execucao", "dumpsys activity services"),
    ("10-processos-lru", "dumpsys activity lru"),
    ("11-pacotes-sistema", "pm list packages -s -f"),
    ("12-pacotes-terceiros", "pm list packages -3 -f"),
    ("13-pacotes-desativados", "pm list packages -d"),
    ("14-animacoes", "; ".join(f"echo {k}=$(settings get global {k})" for k in ANIM_KEYS)),
    ("15-usagestats", "dumpsys usagestats"),
    ("16-logcat-erros", "logcat -d -v time -t 3000 *:E"),
    ("17-logcat-crash", "logcat -d -v time -b crash"),
    ("18-conectividade", "dumpsys connectivity"),
    ("19-wifi", "dumpsys wifi"),
    ("20-bluetooth", "dumpsys bluetooth_manager"),
    ("21-dispositivos-entrada", "dumpsys input"),
    ("22-termico", "dumpsys thermalservice"),
    ("23-hdmi-cec", "dumpsys hdmi_control"),
    ("24-settings-global", "settings list global"),
    ("25-ip", "ip addr; ip route"),
    ("26-diskstats", "dumpsys diskstats"),
]


def load_config() -> dict:
    cfg = {"ip": "", "port": 5555, "auto_reconnect": True, "adb_path": "", "scrcpy_path": "",
           "scrcpy_args": ["--max-size=1280", "--max-fps=30", "--video-bit-rate=4M"]}
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1040x720")
        self.minsize(900, 600)
        self.cfg = load_config()
        self.kb = KnowledgeBase()
        self.hist = History()
        self.adb_path = find_tool("adb", self.cfg.get("adb_path", ""))
        self.scrcpy_path = find_tool("scrcpy", self.cfg.get("scrcpy_path", ""))
        self.client = AdbClient(self.adb_path or "adb")
        self.want_connected = False
        self.ever_connected = False
        self.connect_failure: str | None = None
        self.last_state = "desconectado"
        self._q: queue.Queue = queue.Queue()
        self._closing = False
        self.pkg_rows: dict[str, dict] = {}

        self._build_ui()
        self.after(80, self._drain_queue)
        threading.Thread(target=self._watchdog, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if not self.adb_path:
            self.log("ADB nao encontrado. Rode o INSTALAR.bat novamente.")
            messagebox.showwarning(APP_TITLE, "O ADB (ferramenta de conexao com a TV) nao foi encontrado.\n\n"
                                              "Feche este painel e rode o INSTALAR.bat de novo.")
        elif self.cfg.get("ip"):
            self.do_connect()
        else:
            self.after(400, self.open_wizard)

    def open_wizard(self) -> None:
        ConnectWizard(self)

    # ------------------------------------------------------------------ infra
    def bg(self, fn, callback=None) -> None:
        """Executa fn em thread; callback(result) roda na thread da interface."""
        def worker():
            try:
                res = fn()
            except Exception as e:  # noqa: BLE001 - mostrar qualquer erro ao usuario
                res = e
            if callback:
                self._q.put((callback, res))
        threading.Thread(target=worker, daemon=True).start()

    def _drain_queue(self) -> None:
        try:
            while True:
                cb, res = self._q.get_nowait()
                if isinstance(res, Exception):
                    self.log(f"ERRO: {res}")
                else:
                    cb(res)
        except queue.Empty:
            pass
        if not self._closing:
            self.after(80, self._drain_queue)

    def log(self, msg: str) -> None:
        line = f"{datetime.now():%H:%M:%S}  {msg}"
        self.status_var.set(line)
        self.conn_log.configure(state="normal")
        self.conn_log.insert("end", line + "\n")
        self.conn_log.see("end")
        self.conn_log.configure(state="disabled")
        try:
            (ROOT / "logs").mkdir(exist_ok=True)
            with open(ROOT / "logs" / f"app-{datetime.now():%Y%m%d}.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now():%Y-%m-%d} {line}\n")
        except OSError:
            pass

    def connected(self, warn: bool = True) -> bool:
        if self.last_state == "device":
            return True
        if warn:
            messagebox.showwarning(APP_TITLE, f"Dispositivo nao conectado (estado: {self.last_state}).")
        return False

    def _on_close(self) -> None:
        self._closing = True
        self.client.close_key_shell()
        self.destroy()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Big.TButton", font=("Segoe UI", 12), padding=8)
        style.configure("State.TLabel", font=("Segoe UI", 11, "bold"))

        self.status_var = tk.StringVar(value="Pronto.")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken").pack(fill="x", side="bottom")

        self._tab_connection()
        self._tab_control()
        self._tab_diagnostics()
        self._tab_optimization()
        self._tab_history()
        self._tab_bluetooth()
        self.bind_all("<KeyPress>", self._on_key)

    # ---- Conexao
    def _tab_connection(self) -> None:
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Conexao")
        top = ttk.LabelFrame(f, text="Dispositivo", padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="IP:").grid(row=0, column=0, sticky="w")
        self.ip_var = tk.StringVar(value=self.cfg.get("ip", ""))
        ttk.Entry(top, textvariable=self.ip_var, width=18).grid(row=0, column=1, padx=4)
        ttk.Label(top, text="Porta:").grid(row=0, column=2, sticky="w")
        self.port_var = tk.StringVar(value=str(self.cfg.get("port", 5555)))
        ttk.Entry(top, textvariable=self.port_var, width=7).grid(row=0, column=3, padx=4)
        ttk.Button(top, text="Conectar", command=self.do_connect).grid(row=0, column=4, padx=4)
        ttk.Button(top, text="Testar conexao", command=self.do_test_connection).grid(row=2, column=3, columnspan=2, sticky="w")
        ttk.Button(top, text="Assistente de conexao", command=self.open_wizard).grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Button(top, text="Desconectar", command=self.do_disconnect).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="Parear (depuracao sem fio)", command=self.do_pair).grid(row=0, column=6, padx=4)
        ttk.Button(top, text="Procurar na rede", command=self.do_discover).grid(row=0, column=7, padx=4)
        self.sweep_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="varredura leve /24", variable=self.sweep_var).grid(row=0, column=8)

        self.auto_var = tk.BooleanVar(value=bool(self.cfg.get("auto_reconnect", True)))
        ttk.Checkbutton(top, text="Reconectar automaticamente", variable=self.auto_var,
                        command=self._save_auto).grid(row=1, column=0, columnspan=3, sticky="w", pady=6)
        ttk.Label(top, text="Status ADB:").grid(row=1, column=3, sticky="e")
        self.state_var = tk.StringVar(value="desconectado")
        self.state_lbl = ttk.Label(top, textvariable=self.state_var, style="State.TLabel", foreground="gray")
        self.state_lbl.grid(row=1, column=4, columnspan=2, sticky="w")
        ttk.Button(top, text="Abrir espelhamento (scrcpy)", command=self.open_scrcpy).grid(row=1, column=6, padx=4)
        ttk.Button(top, text="scrcpy somente controle", command=lambda: self.open_scrcpy(no_video=True)).grid(row=1, column=7, columnspan=2)

        tools = ttk.LabelFrame(f, text="Ferramentas", padding=8)
        tools.pack(fill="x", pady=8)
        ttk.Label(tools, text=f"adb: {self.adb_path or 'NAO ENCONTRADO'}").pack(anchor="w")
        ttk.Label(tools, text=f"scrcpy: {self.scrcpy_path or 'NAO ENCONTRADO'}").pack(anchor="w")
        ttk.Label(tools, text="Dica: conteudo com DRM (Netflix, Prime...) normalmente aparece preto no espelhamento.",
                  foreground="gray").pack(anchor="w")

        info = ttk.LabelFrame(f, text="Registro", padding=4)
        info.pack(fill="both", expand=True)
        self.conn_log = ScrolledText(info, height=12, state="disabled", font=("Consolas", 9))
        self.conn_log.pack(fill="both", expand=True)

    def _save_auto(self) -> None:
        self.cfg["auto_reconnect"] = bool(self.auto_var.get())
        save_config(self.cfg)

    def _set_state(self, st: str) -> None:
        self.last_state = st
        self.state_var.set({"device": "conectado e autorizado", "unauthorized": "aguardando autorizacao na TV",
                            "offline": "offline"}.get(st, st))
        self.state_lbl.configure(foreground={"device": "green", "unauthorized": "orange"}.get(st, "red"))

    def do_connect(self) -> None:
        if not self.adb_path:
            messagebox.showerror(APP_TITLE, "ADB nao encontrado. Rode scripts\\00-Preparar-Windows.ps1.")
            return
        ip = self.ip_var.get().strip()
        if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip):
            messagebox.showwarning(APP_TITLE, "Informe o IP mostrado na TV:\nConfiguracoes > Preferencias do dispositivo > Sobre > Status.")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            port = 5555
        self.cfg.update(ip=ip, port=port)
        save_config(self.cfg)
        self.connect_failure = None
        self.log(f"Conectando a {ip}:{port} ...")

        def work():
            tcp = N.probe_tcp(ip, port, 2.5)
            if tcp != "open":  # nao chama o adb (evita 15 s de espera) e explica o motivo
                return ("diag",) + self._run_diagnosis(ip, port, tcp)
            r = self.client.connect(ip, port)
            st = self.client.state()
            for _ in range(15):  # ate ~30 s para autorizar na TV
                if st != "unauthorized":
                    break
                time.sleep(2)
                st = self.client.state()
            return r, st

        def done(res):
            if res[0] == "diag":
                _, text, suggested = res
                self.want_connected = False
                self._set_state("desconectado")
                self.connect_failure = text
                for line in text.splitlines():
                    self.log(line)
                if suggested:
                    self.port_var.set(str(suggested))
                if not any(isinstance(w, ConnectWizard) for w in self.winfo_children()):
                    messagebox.showwarning(APP_TITLE, text)
                return
            r, st = res
            self.want_connected = True
            self.log(r.text or f"rc={r.rc}")
            self._set_state(st)
            if st == "unauthorized":
                self.log("Autorize na TV: 'Permitir depuracao USB?' -> marque 'Sempre permitir' -> OK.")
            elif st == "device":
                self.ever_connected = True
                self.log("Conectado.")
                self.bg(self._device_header, lambda t: self.log(t))
                self.refresh_apps()
        self.bg(work, done)

    def _run_diagnosis(self, ip: str, port: int, tcp: str | None = None) -> tuple[str, int | None]:
        if tcp is None:
            tcp = N.probe_tcp(ip, port, 2.5)
        ping = N.ping_host(ip) if tcp != "open" else True
        mdns = self.client.run("mdns", "services", use_serial=False, timeout=10).out if self.adb_path else ""
        return N.diagnose(ip, port, tcp, ping, N.local_ipv4(), N.mdns_ports(mdns, ip))

    def do_test_connection(self) -> None:
        ip = self.ip_var.get().strip()
        if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip):
            messagebox.showwarning(APP_TITLE, "Informe o IP mostrado na TV.")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            port = 5555
        self.log(f"Testando a rede ate {ip}:{port} ...")

        def done(res):
            text, suggested = res
            for line in text.splitlines():
                self.log(line)
            if suggested:
                self.port_var.set(str(suggested))
            messagebox.showinfo(APP_TITLE, text)
        self.bg(lambda: self._run_diagnosis(ip, port), done)

    def _device_header(self) -> str:
        g = self.client.getprop
        return (f"{g('ro.product.manufacturer')} {g('ro.product.model')} | Android {g('ro.build.version.release')} "
                f"(SDK {g('ro.build.version.sdk')}) | firmware {g('ro.build.display.id')}")

    def do_disconnect(self) -> None:
        self.want_connected = False
        self.bg(self.client.disconnect, lambda r: (self.log(r.text or "Desconectado."), self._set_state("desconectado")))

    def do_pair(self) -> None:
        hp = simpledialog.askstring(APP_TITLE, "IP:porta exibidos em 'Parear dispositivo com codigo':", parent=self)
        if not hp:
            return
        code = simpledialog.askstring(APP_TITLE, "Codigo de pareamento (6 digitos):", parent=self)
        if not code:
            return
        self.bg(lambda: self.client.pair(hp.strip(), code.strip()),
                lambda r: self.log((r.text or "") + "\nApos parear, informe a porta de 'Depuracao sem fio' e clique Conectar."))

    def do_discover(self) -> None:
        sweep = self.sweep_var.get()
        self.log("Procurando dispositivos ADB na rede (mDNS + vizinhos ARP" + (" + varredura leve" if sweep else "") + ")...")
        self.bg(lambda: discover_devices(self.client, sweep), self._discover_done)

    def _discover_done(self, found: list[tuple[str, int, str]]) -> None:
        if not found:
            self.log("Nada encontrado. Veja o IP na TV (Configuracoes > Preferencias do dispositivo > Sobre > Status) e confirme a depuracao ADB ativa.")
            return
        for ip, port, src in found:
            self.log(f"Encontrado: {ip}:{port} ({src})")
        if len({f[0] for f in found}) == 1:
            self.ip_var.set(found[0][0])
            self.port_var.set(str(found[0][1]))

    def _watchdog(self) -> None:
        fails = 0
        while not self._closing:
            delay = 10
            if self.adb_path and self.client.serial and self.want_connected and self.ever_connected:
                st = self.client.state()
                if st != self.last_state:
                    self._q.put((self._set_state, st))
                if st == "device":
                    if fails:
                        self._q.put((self.log, "Conexao restabelecida."))
                    fails = 0
                elif self.cfg.get("auto_reconnect", True) and st != "unauthorized":
                    fails += 1
                    ip, port = self.client.serial.split(":")
                    if N.probe_tcp(ip, int(port), 1.5) == "open":
                        self.client.close_key_shell()
                        r = self.client.connect(ip, int(port))
                        self._q.put((self.log, f"Reconexao automatica ({fails}): {r.text}"))
                    elif fails == 1:
                        self._q.put((self.log, f"Conexao com a TV perdida (TV desligada ou dormindo?). "
                                               "Vou reconectar sozinho quando ela voltar."))
                    delay = min(120, 10 * min(fails, 8))
            time.sleep(delay)

    def open_scrcpy(self, no_video: bool = False) -> None:
        if not self.connected():
            return
        if not self.scrcpy_path:
            messagebox.showerror(APP_TITLE, "scrcpy nao encontrado. Rode scripts\\00-Preparar-Windows.ps1.")
            return
        args = [self.scrcpy_path, "-s", self.client.serial, "--window-title=Mi TV Stick", *self.cfg.get("scrcpy_args", [])]
        if no_video:
            args += ["--no-video", "--no-audio"]
        env = dict(os.environ, ADB=self.adb_path or "adb")  # evita conflito de versoes do adb
        try:
            subprocess.Popen(args, env=env, creationflags=CREATE_NO_WINDOW if no_video else 0)
            self.log("scrcpy: " + " ".join(args[1:]))
        except OSError as e:
            self.log(f"Falha ao abrir scrcpy: {e}")

    # ---- Controle
    def _tab_control(self) -> None:
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Controle remoto")
        self.control_tab = f
        pad = ttk.LabelFrame(f, text="Navegacao", padding=10)
        pad.grid(row=0, column=0, sticky="nw", padx=6)
        B = lambda parent, txt, key, r, c, **kw: ttk.Button(parent, text=txt, style="Big.TButton", width=kw.pop("w", 8),
                                                             command=lambda: self.send_key(key)).grid(row=r, column=c, padx=3, pady=3, **kw)
        B(pad, "▲", "UP", 0, 1)
        B(pad, "◀", "LEFT", 1, 0)
        B(pad, "OK", "OK", 1, 1)
        B(pad, "▶", "RIGHT", 1, 2)
        B(pad, "▼", "DOWN", 2, 1)
        B(pad, "Voltar", "BACK", 3, 0)
        B(pad, "Home", "HOME", 3, 1)
        B(pad, "Menu", "MENU", 3, 2)
        B(pad, "Config.", "SETTINGS", 4, 0)
        B(pad, "Assist.", "ASSIST", 4, 1)
        B(pad, "Recentes", "RECENTS", 4, 2)

        media = ttk.LabelFrame(f, text="Midia e volume", padding=10)
        media.grid(row=1, column=0, sticky="nw", padx=6, pady=(8, 0))
        for i, (t, k) in enumerate([("⏮", "PREV"), ("⏪", "REW"), ("⏯", "PLAYPAUSE"), ("⏩", "FF"), ("⏭", "NEXT"), ("⏹", "STOP")]):
            B(media, t, k, 0, i, w=4)
        for i, (t, k) in enumerate([("Vol -", "VOLDOWN"), ("Mudo", "MUTE"), ("Vol +", "VOLUP"), ("Dormir", "SLEEP"), ("Acordar", "WAKEUP")]):
            B(media, t, k, 1, i, w=6)
        ttk.Label(media, text="Volume depende do HDMI-CEC da TV.", foreground="gray").grid(row=2, column=0, columnspan=6, sticky="w")

        txt = ttk.LabelFrame(f, text="Digitar texto na TV (campo de busca focado)", padding=8)
        txt.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=8)
        self.text_var = tk.StringVar()
        e = ttk.Entry(txt, textvariable=self.text_var, width=50)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda _e: self.send_text())
        ttk.Button(txt, text="Enviar", command=self.send_text).pack(side="left")

        apps = ttk.LabelFrame(f, text="Aplicativos", padding=8)
        apps.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=6)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(1, weight=1)
        sc = ttk.Frame(apps)
        sc.pack(fill="x")
        for i, name in enumerate(STREAMING_SHORTCUTS):
            ttk.Button(sc, text=name, width=14, command=lambda n=name: self.launch(STREAMING_SHORTCUTS[n])).grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
        ttk.Label(apps, text="Instalados (com icone na tela inicial):").pack(anchor="w", pady=(8, 0))
        self.apps_list = tk.Listbox(apps, height=12)
        self.apps_list.pack(fill="both", expand=True)
        self.apps_list.bind("<Double-1>", lambda _e: self._launch_selected())
        row = ttk.Frame(apps)
        row.pack(fill="x", pady=4)
        ttk.Button(row, text="Abrir", command=self._launch_selected).pack(side="left")
        ttk.Button(row, text="Forcar parada", command=self._stop_selected).pack(side="left", padx=4)
        ttk.Button(row, text="Atualizar lista", command=self.refresh_apps).pack(side="left")

        ttk.Label(f, text="Teclado (com esta aba aberta e fora de campos de texto): setas, Enter=OK, Backspace/Esc=Voltar, "
                          "H=Home, M=Menu, Espaco=Play/Pause, +/-=Volume, X=Mudo.", foreground="gray",
                  wraplength=900).grid(row=3, column=0, columnspan=2, sticky="w", pady=6)

    KEYMAP = {"Up": "UP", "Down": "DOWN", "Left": "LEFT", "Right": "RIGHT", "Return": "OK", "KP_Enter": "OK",
              "BackSpace": "BACK", "Escape": "BACK", "h": "HOME", "m": "MENU", "space": "PLAYPAUSE",
              "plus": "VOLUP", "KP_Add": "VOLUP", "equal": "VOLUP", "minus": "VOLDOWN", "KP_Subtract": "VOLDOWN",
              "x": "MUTE", "n": "NEXT", "p": "PREV", "f": "FF", "r": "REW"}

    def _on_key(self, ev) -> None:
        if self.nb.select() != str(self.control_tab):
            return
        if isinstance(ev.widget, (tk.Entry, ttk.Entry, tk.Text)):
            return
        key = self.KEYMAP.get(ev.keysym)
        if key:
            self.send_key(key)

    def send_key(self, key: str) -> None:
        if not self.connected(warn=False):
            self.log("Nao conectado.")
            return
        self.bg(lambda: self.client.key(key), lambda ok: None if ok else self.log(f"Falha ao enviar {key}"))

    def send_text(self) -> None:
        t = self.text_var.get()
        if t and self.connected():
            self.bg(lambda: self.client.text(t), lambda ok: self.log("Texto enviado." if ok else "Falha ao enviar texto."))
            self.text_var.set("")

    def refresh_apps(self) -> None:
        if not self.connected(warn=False):
            return

        def work():
            r = self.client.shell("cmd package query-activities --brief -a android.intent.action.MAIN "
                                  "-c android.intent.category.LEANBACK_LAUNCHER")
            pkgs = sorted({l.strip().split("/")[0] for l in r.out.splitlines() if "/" in l})
            if not pkgs:  # firmwares antigos sem query-activities
                pkgs = P.parse_packages(self.client.shell("pm list packages -3").out)
            return pkgs

        def done(pkgs):
            items = sorted(((self.kb.classify(p, third_party=True).name, p) for p in pkgs), key=lambda t: t[0].lower())
            self.app_pkgs = [p for _, p in items]
            self.apps_list.delete(0, "end")
            for name, p in items:
                self.apps_list.insert("end", f"{name}   —   {p}")
        self.bg(work, done)

    def _selected_app(self) -> str | None:
        sel = self.apps_list.curselection()
        pkgs = getattr(self, "app_pkgs", [])
        return pkgs[sel[0]] if sel and sel[0] < len(pkgs) else None

    def _launch_selected(self) -> None:
        p = self._selected_app()
        if p:
            self.launch(p)

    def _stop_selected(self) -> None:
        p = self._selected_app()
        if p and self.connected():
            self.bg(lambda: self.client.force_stop(p), lambda r: self.log(f"force-stop {p}: {r.text or 'ok'}"))

    def launch(self, pkg: str) -> None:
        if not self.connected():
            return

        def done(r):
            bad = "No activities found" in r.text or "aborted" in r.text or not r.ok
            self.log(f"Nao foi possivel abrir {pkg} (instalado?)" if bad else f"Aberto: {pkg}")
        self.bg(lambda: self.client.launch(pkg), done)

    # ---- Diagnostico
    def _tab_diagnostics(self) -> None:
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Diagnostico")
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        for txt, cmd in [("Resumo rapido", self.diag_summary), ("Coleta completa (salvar)", self.diag_full),
                         ("Comparar 2 ultimas coletas", self.diag_compare), ("Processos (top)", self.diag_top),
                         ("Apps instalados", self.diag_apps), ("Erros recentes (logcat)", self.diag_errors)]:
            ttk.Button(bar, text=txt, command=cmd).pack(side="left", padx=3)
        ttk.Button(bar, text="Abrir pasta reports", command=lambda: open_folder(REPORTS)).pack(side="right")
        self.diag_text = ScrolledText(f, font=("Consolas", 9))
        self.diag_text.pack(fill="both", expand=True, pady=6)

    def _show(self, widget: ScrolledText, text: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    def collect_metrics(self) -> dict:
        c = self.client
        mem = P.parse_meminfo(c.shell("cat /proc/meminfo").out)
        df = P.parse_df(c.shell("df /data").out)
        pss = P.parse_pss_by_process(c.shell("dumpsys meminfo", timeout=60).out)
        anim = {k: c.shell(f"settings get global {k}").out.strip() for k in ANIM_KEYS}
        load = c.shell("cat /proc/loadavg").out.strip()
        nproc = len([l for l in c.shell("ps -A -o PID").out.splitlines()[1:] if l.strip()])
        enabled = len(P.parse_packages(c.shell("pm list packages -e").out))
        disabled = len(P.parse_packages(c.shell("pm list packages -d").out))
        g = c.getprop
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "modelo": f"{g('ro.product.manufacturer')} {g('ro.product.model')} ({g('ro.product.device')})",
            "android": f"{g('ro.build.version.release')} (SDK {g('ro.build.version.sdk')})",
            "firmware": g("ro.build.display.id"), "patch": g("ro.build.version.security_patch"),
            "plataforma": f"{g('ro.board.platform')} / {g('ro.hardware')}",
            "uptime": c.shell("uptime").out.strip(),
            "mem_total_kb": mem.get("MemTotal"), "mem_available_kb": mem.get("MemAvailable"),
            "swap_total_kb": mem.get("SwapTotal"), "swap_free_kb": mem.get("SwapFree"),
            "data": df[0] if df else {}, "loadavg": load, "processos": nproc,
            "pacotes_ativos": enabled, "pacotes_desativados": disabled, "animacoes": anim,
            "top_pss_kb": dict(sorted(pss.items(), key=lambda kv: -kv[1])[:15]),
        }

    def format_metrics(self, m: dict) -> str:
        swap_used = (m["swap_total_kb"] or 0) - (m["swap_free_kb"] or 0)
        lines = [
            f"Coleta: {m['timestamp']}", f"Modelo: {m['modelo']}", f"Android: {m['android']}",
            f"Firmware: {m['firmware']}   Patch: {m['patch']}", f"Plataforma: {m['plataforma']}",
            f"Uptime: {m['uptime']}", "",
            f"RAM total: {P.kb_to_mb(m['mem_total_kb'])}   disponivel: {P.kb_to_mb(m['mem_available_kb'])}",
            f"Swap/ZRAM: {P.kb_to_mb(m['swap_total_kb'])} total, {P.kb_to_mb(swap_used)} em uso",
            f"/data: {m['data']}", f"Load average: {m['loadavg']}   Processos: {m['processos']}",
            f"Pacotes ativos: {m['pacotes_ativos']}   desativados: {m['pacotes_desativados']}",
            f"Animacoes: {m['animacoes']}", "", "Maiores consumidores de RAM (PSS):",
        ]
        lines += [f"  {kb / 1024:8.1f} MB  {self.kb.classify(name).name if '.' in name else name}  ({name})"
                  for name, kb in m["top_pss_kb"].items()]
        lines += ["", "Observacao: Android usa RAM livre como cache; isso nao e desperdicio. Avalie MemAvailable,",
                  "uso de swap e travamentos percebidos, sempre comparando coletas feitas em condicoes parecidas."]
        return "\n".join(lines)

    def diag_summary(self) -> None:
        if self.connected():
            self._show(self.diag_text, "Coletando...")
            self.bg(self.collect_metrics, lambda m: self._show(self.diag_text, self.format_metrics(m)))

    def diag_full(self) -> None:
        if not self.connected():
            return
        self._show(self.diag_text, "Coleta completa em andamento (pode levar 1-2 minutos)...")

        def work():
            d = REPORTS / f"diagnostico-{datetime.now():%Y%m%d-%H%M%S}"
            d.mkdir(parents=True)
            for name, cmd in DIAG_COMMANDS:
                r = self.client.shell(cmd, timeout=90)
                (d / f"{name}.txt").write_text(f"# adb shell {cmd}\n{r.text}", encoding="utf-8")
            m = self.collect_metrics()
            (d / "resumo.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
            (d / "resumo.md").write_text("# Resumo do diagnostico\n\n```\n" + self.format_metrics(m) + "\n```\n", encoding="utf-8")
            return d, m

        self.bg(work, lambda res: self._show(self.diag_text, f"Salvo em {res[0]}\n\n" + self.format_metrics(res[1])))

    def diag_compare(self) -> None:
        runs = sorted(REPORTS.glob("diagnostico-*/resumo.json"))
        if len(runs) < 2:
            messagebox.showinfo(APP_TITLE, "Sao necessarias pelo menos 2 coletas completas (antes e depois).")
            return
        a, b = (json.loads(p.read_text(encoding="utf-8")) for p in runs[-2:])
        self._show(self.diag_text, compare_metrics(a, b, runs[-2].parent.name, runs[-1].parent.name))

    def diag_top(self) -> None:
        if self.connected():
            self.bg(lambda: self.client.shell("top -b -n 1 -m 25").text, lambda t: self._show(self.diag_text, t))

    def diag_apps(self) -> None:
        if not self.connected():
            return

        def work():
            s = P.parse_packages(self.client.shell("pm list packages -s").out)
            t = P.parse_packages(self.client.shell("pm list packages -3").out)
            d = set(P.parse_packages(self.client.shell("pm list packages -d").out))
            def fmt(p, third):
                i = self.kb.classify(p, third_party=third)
                return f"  {i.name:<45} {i.recommendation:<28} {p}{'  [desativado]' if p in d else ''}"
            return (f"Apps instalados por você ({len(t)}):\n" + "\n".join(fmt(p, True) for p in t) +
                    f"\n\nApps de fábrica/sistema ({len(s)}):\n" + "\n".join(fmt(p, False) for p in s))
        self.bg(work, lambda t: self._show(self.diag_text, t))

    def diag_errors(self) -> None:
        if self.connected():
            self.bg(lambda: self.client.shell("logcat -d -v time -t 800 *:E", timeout=40).text,
                    lambda t: self._show(self.diag_text, t or "(sem erros no buffer atual)"))

    # ---- Otimizacao
    def _tab_optimization(self) -> None:
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Otimizacao")
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        ttk.Button(bar, text="Carregar e classificar pacotes", command=self.load_packages).pack(side="left")
        ttk.Label(bar, text="  Filtro:").pack(side="left")
        self.filter_var = tk.StringVar(value=FILTROS[0])
        cb = ttk.Combobox(bar, textvariable=self.filter_var, state="readonly", width=34, values=FILTROS)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda _e: self._fill_pkg_tree())
        ttk.Button(bar, text="Desativar selecionado", command=self.disable_selected).pack(side="right", padx=3)
        ttk.Button(bar, text="Reativar selecionado", command=self.enable_selected).pack(side="right", padx=3)

        cols = ("nome", "recomendacao", "ram", "uso", "estado", "pacote")
        self.pkg_tree = scrolled_tree(f, cols, ("O que é", "Recomendação", "RAM agora", "Último uso", "Estado", "Nome técnico"),
                                      (300, 185, 75, 135, 80, 300), height=12)
        for cat, cor in CORES.items():
            self.pkg_tree.tag_configure(cat, foreground=cor)
        self.pkg_tree.bind("<<TreeviewSelect>>", lambda _e: self._pkg_details())
        ttk.Label(f, text="Clique em um item para ver a explicação.  Verde = pode desativar se não usa · Laranja = depende do uso · "
                          "Azul = app seu · Vermelho = sem informação · Cinza = manter", foreground="gray", wraplength=980).pack(anchor="w")
        self.pkg_detail = tk.Text(f, height=7, wrap="word", font=("Segoe UI", 10), relief="flat", background=self.cget("background"))
        self.pkg_detail.tag_configure("titulo", font=("Segoe UI", 12, "bold"))
        self.pkg_detail.tag_configure("rotulo", font=("Segoe UI", 10, "bold"))
        self.pkg_detail.pack(fill="x", pady=(4, 0))

        an = ttk.LabelFrame(f, text="Animacoes do sistema (reduzir deixa a navegacao mais agil; nao afeta video)", padding=6)
        an.pack(fill="x", pady=6)
        self.anim_var = tk.StringVar(value="(nao lido)")
        ttk.Label(an, textvariable=self.anim_var).pack(side="left")
        for v in ("1.0", "0.5", "0"):
            ttk.Button(an, text=f"Definir {v}x", command=lambda v=v: self.set_animations(v)).pack(side="right", padx=2)
        ttk.Button(an, text="Ler", command=self.read_animations).pack(side="right", padx=8)

    def load_packages(self) -> None:
        if not self.connected():
            return
        self.log("Lendo pacotes, uso de RAM e estatisticas de uso...")

        def work():
            c = self.client
            sysp = set(P.parse_packages(c.shell("pm list packages -s").out))
            third = set(P.parse_packages(c.shell("pm list packages -3").out))
            dis = set(P.parse_packages(c.shell("pm list packages -d").out))
            pss = P.parse_pss_by_process(c.shell("dumpsys meminfo", timeout=60).out)
            usage = P.parse_usagestats_last_used(c.shell("dumpsys usagestats", timeout=60).out)
            rows = {}
            for p in sorted(sysp | third):
                info = self.kb.classify(p, third_party=p in third)
                rows[p] = {"info": info, "tipo": "terceiro" if p in third else "sistema",
                           "estado": "desativado" if p in dis else "ativo",
                           "ram": f"{pss[p] / 1024:.0f} MB" if p in pss else "-", "uso": usage.get(p, "sem registro")}
            return rows

        def done(rows):
            self.pkg_rows = rows
            self._fill_pkg_tree()
            cats: dict[str, int] = {}
            for r in rows.values():
                cats[r["info"].category] = cats.get(r["info"].category, 0) + 1
            self.log(f"{len(rows)} pacotes: {cats}")
            self.export_classification(rows)
        self.bg(work, done)

    def export_classification(self, rows: dict) -> None:
        REPORTS.mkdir(exist_ok=True)
        p = REPORTS / f"classificacao-{datetime.now():%Y%m%d-%H%M%S}.md"
        lines = ["# Aplicativos da TV, explicados", "", f"Gerado em {datetime.now():%d/%m/%Y %H:%M}. Nada foi alterado.", "",
                 "| O que é | Recomendação | Para que serve | Se desativar | RAM agora | Último uso | Estado | Nome técnico |",
                 "|---|---|---|---|---|---|---|---|"]
        for name, r in sorted(rows.items(), key=lambda kv: (ORDEM.get(kv[1]["info"].category, 9), kv[1]["info"].name, kv[0])):
            i = r["info"]
            lines.append(f"| **{i.name}** | {i.recommendation} | {i.function} | {i.effect} | {r['ram']} | {r['uso']} | {r['estado']} | `{name}` |")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.log(f"Tabela salva em {p}")

    def _fill_pkg_tree(self) -> None:
        self.pkg_tree.delete(*self.pkg_tree.get_children())
        flt = self.filter_var.get()
        cats = FILTRO_CATS.get(flt)
        rows = sorted(self.pkg_rows.items(), key=lambda kv: (ORDEM.get(kv[1]["info"].category, 9), kv[1]["info"].name, kv[0]))
        for name, r in rows:
            i = r["info"]
            if cats is not None and i.category not in cats:
                continue
            if flt == "Desativados" and r["estado"] != "desativado":
                continue
            self.pkg_tree.insert("", "end", iid=name, tags=(i.category,),
                                 values=(i.name, i.recommendation, r["ram"], r["uso"], r["estado"], name))

    def _selected_pkg(self) -> str | None:
        sel = self.pkg_tree.selection()
        return sel[0] if sel else None

    def _pkg_details(self) -> None:
        p = self._selected_pkg()
        if not p:
            return
        r = self.pkg_rows[p]
        i = r["info"]
        d = self.pkg_detail
        d.configure(state="normal")
        d.delete("1.0", "end")
        d.insert("end", f"{i.name}\n", "titulo")
        for rot, val in (("Recomendação: ", i.recommendation + ("  (protegido: o programa não deixa desativar)" if i.protected else "")),
                         ("Para que serve: ", i.function), ("Se desativar: ", i.effect),
                         ("Uso de memória agora: ", f"{r['ram']}    Último uso registrado: {r['uso']}    Estado: {r['estado']}"),
                         ("Nome técnico: ", p)):
            d.insert("end", rot, "rotulo")
            d.insert("end", val + "\n")
        d.configure(state="disabled")

    def disable_selected(self) -> None:
        p = self._selected_pkg()
        if not p or not self.connected():
            return
        r = self.pkg_rows[p]
        i = r["info"]
        if i.protected or i.category == "Essencial":
            messagebox.showerror(APP_TITLE, f"{i.name} é necessário para a TV funcionar (ou é um app de streaming protegido).\n\n"
                                            f"Para que serve: {i.function}\n\nO programa não permite desativar.")
            return
        if r["estado"] == "desativado":
            messagebox.showinfo(APP_TITLE, "Pacote ja esta desativado.")
            return
        msg = (f"Desativar \"{i.name}\"?\n\nPara que serve: {i.function}\nSe desativar: {i.effect}\n"
               f"Memória agora: {r['ram']}   Último uso: {r['uso']}\n\n"
               "Nenhum dado é apagado e nada é desinstalado. Dá para desfazer na aba Histórico e reversão.\n"
               f"(nome técnico: {p})")
        if i.category == "Desconhecido":
            typed = simpledialog.askstring(APP_TITLE, msg + "\n\nPacote NAO classificado. Digite o nome completo para confirmar:", parent=self)
            if typed != p:
                self.log("Desativacao cancelada.")
                return
        elif not messagebox.askyesno(APP_TITLE, msg, icon="warning"):
            return
        self._change_package(p, disable=True)

    def enable_selected(self) -> None:
        p = self._selected_pkg()
        if p and self.connected() and self.pkg_rows[p]["estado"] == "desativado":
            if messagebox.askyesno(APP_TITLE, f"Reativar \"{self.pkg_rows[p]['info'].name}\"?\n(nome técnico: {p})"):
                self._change_package(p, disable=False)

    def _change_package(self, p: str, disable: bool) -> None:
        if not is_valid_package(p):
            return

        def work():
            if disable:
                motivo = P.home_guard(
                    p,
                    self.client.shell("cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME").out,
                    self.client.shell("cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME").out)
                if motivo:
                    return False, "RECUSADO: " + motivo, None
            cmd = f"pm disable-user --user 0 {p}" if disable else f"pm enable --user 0 {p}"
            r = self.client.shell(cmd)
            now_disabled = p in P.parse_packages(self.client.shell("pm list packages -d").out)
            ok = now_disabled == disable
            rev = ["pm", "enable", "--user", "0", p] if disable else ["pm", "disable-user", "--user", "0", p]
            e = self.hist.add("pacote", p, "enabled" if disable else "disabled-user",
                              ("disabled-user" if disable else "enabled") if ok else "falhou", rev, r.text)
            return ok, r.text, e

        def done(res):
            ok, out, e = res
            if e is None:
                self.log(out)
                messagebox.showerror(APP_TITLE, out)
                return
            self.log(f"{'Desativado' if disable else 'Reativado'} {p}: {out} (historico id {e['id']})" if ok else f"FALHOU em {p}: {out}")
            if ok:
                self.pkg_rows[p]["estado"] = "desativado" if disable else "ativo"
                self._fill_pkg_tree()
            self.refresh_history()
        self.bg(work, done)

    def read_animations(self) -> None:
        if self.connected():
            self.bg(lambda: {k: self.client.shell(f"settings get global {k}").out.strip() for k in ANIM_KEYS},
                    lambda d: self.anim_var.set("  ".join(f"{k.split('_')[0]}={v}" for k, v in d.items())))

    def set_animations(self, value: str) -> None:
        if not self.connected():
            return
        if not messagebox.askyesno(APP_TITLE, f"Definir as 3 escalas de animacao para {value}x?\n"
                                              "Valores atuais serao registrados para reversao.\n(1.0 = padrao de fabrica)"):
            return

        def work():
            out = []
            for k in ANIM_KEYS:
                before = self.client.shell(f"settings get global {k}").out.strip()
                self.client.shell(f"settings put global {k} {value}")
                after = self.client.shell(f"settings get global {k}").out.strip()
                rev = ["settings", "delete", "global", k] if before in ("null", "") else ["settings", "put", "global", k, before]
                self.hist.add("configuracao", k, before, after, rev, "ok" if after == value else "verificar")
                out.append(f"{k}: {before} -> {after}")
            return "\n".join(out)

        self.bg(work, lambda t: (self.log(t.replace("\n", " | ")), self.read_animations(), self.refresh_history()))

    # ---- Historico
    def _tab_history(self) -> None:
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Historico e reversao")
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        ttk.Button(bar, text="Atualizar", command=self.refresh_history).pack(side="left")
        ttk.Button(bar, text="Reverter selecionado", command=self.revert_selected).pack(side="left", padx=4)
        ttk.Button(bar, text="Reverter tudo", command=self.revert_all).pack(side="left")
        ttk.Button(bar, text="Exportar procedimento de reversao", command=self.export_revert).pack(side="right")
        cols = ("id", "quando", "origem", "tipo", "alvo", "antes", "depois", "revertido", "reverter")
        self.hist_tree = scrolled_tree(f, cols, [c.capitalize() for c in cols], (40, 140, 75, 90, 230, 90, 100, 70, 300))
        self.refresh_history()

    def refresh_history(self) -> None:
        self.hist_tree.delete(*self.hist_tree.get_children())
        try:
            entries = self.hist.load()
        except ValueError as e:
            self.log(f"historico.json invalido: {e}")
            return
        for e in entries:
            self.hist_tree.insert("", "end", iid=str(e["id"]), values=(
                e["id"], e.get("timestamp", ""), e.get("origem", ""), e.get("tipo", ""), e.get("alvo", ""),
                e.get("antes", ""), e.get("depois", ""), "sim" if e.get("revertido") else "nao", " ".join(e.get("reverter", []))))

    def _revert(self, entries: list[dict]) -> None:
        def work():
            out = []
            for e in entries:
                cmd = e.get("reverter") or []
                if not cmd or cmd[0] not in ("pm", "settings"):
                    out.append(f"{e['id']}: comando de reversao invalido, ignorado")
                    continue
                r = self.client.shell(" ".join(cmd))
                self.hist.mark_reverted(int(e["id"]), r.text or "ok")
                out.append(f"{e['id']} {e.get('alvo')}: {' '.join(cmd)} -> {r.text or 'ok'}")
            return out

        def done(out):
            for line in out:
                self.log("Reversao " + line)
            self.refresh_history()
            if self.pkg_rows:
                self.load_packages()
        self.bg(work, done)

    def revert_selected(self) -> None:
        sel = self.hist_tree.selection()
        if not sel or not self.connected():
            return
        e = next((x for x in self.hist.load() if str(x["id"]) == sel[0]), None)
        if e and not e.get("revertido") and messagebox.askyesno(APP_TITLE, f"Reverter #{e['id']} ({e.get('alvo')})?\n{' '.join(e['reverter'])}"):
            self._revert([e])

    def revert_all(self) -> None:
        if not self.connected():
            return
        pend = [e for e in self.hist.load() if not e.get("revertido") and e.get("depois") != "falhou"]
        if not pend:
            messagebox.showinfo(APP_TITLE, "Nada pendente de reversao.")
            return
        if messagebox.askyesno(APP_TITLE, f"Reverter {len(pend)} alteracao(oes), da mais recente para a mais antiga?"):
            self._revert(sorted(pend, key=lambda e: -int(e["id"])))

    def export_revert(self) -> None:
        entries = [e for e in self.hist.load() if not e.get("revertido") and e.get("depois") != "falhou"]
        REPORTS.mkdir(exist_ok=True)
        p = REPORTS / f"reversao-{datetime.now():%Y%m%d-%H%M%S}.txt"
        serial = self.client.serial or "<IP>:5555"
        lines = ["Procedimento de reversao - execute no PowerShell (ordem: mais recente primeiro)", ""]
        lines += [f"adb -s {serial} shell {' '.join(e['reverter'])}    # #{e['id']} {e.get('alvo')} ({e.get('timestamp')})"
                  for e in sorted(entries, key=lambda e: -int(e["id"]))] or ["(nenhuma alteracao pendente)"]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.log(f"Procedimento salvo em {p}")
        messagebox.showinfo(APP_TITLE, "\n".join(lines[:30]))

    # ---- Bluetooth
    def _tab_bluetooth(self) -> None:
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text="Bluetooth")
        bar = ttk.Frame(f)
        bar.pack(fill="x")
        ttk.Button(bar, text="Analisar Bluetooth e controle (somente leitura)", command=self.bt_analyze).pack(side="left")
        ttk.Label(bar, text="  Nenhum pareamento e alterado por esta aba.", foreground="gray").pack(side="left")
        self.bt_text = ScrolledText(f, font=("Consolas", 9))
        self.bt_text.pack(fill="both", expand=True, pady=6)
        self._show(self.bt_text, BT_PHYSICAL_CHECKLIST)

    def bt_analyze(self) -> None:
        if not self.connected():
            return

        def work():
            c = self.client
            dump = c.shell("dumpsys bluetooth_manager", timeout=40).out
            info = P.parse_bluetooth(dump)
            inp = P.parse_input_devices(c.shell("dumpsys input", timeout=40).out)
            log = c.shell("logcat -d -v time -t 6000", timeout=60).out
            events = P.count_bt_disconnects(log)
            first = log.splitlines()[0][:18] if log.strip() else "?"
            REPORTS.mkdir(exist_ok=True)
            path = REPORTS / f"bluetooth-{datetime.now():%Y%m%d-%H%M%S}.txt"
            path.write_text(dump + "\n\n=== EVENTOS ===\n" + "\n".join(events), encoding="utf-8")
            lines = [f"Bluetooth ligado: {info['enabled']}   estado: {info['state']}   nome: {info['name']}",
                     f"Dispositivos pareados ({len(info['bonded'])}):"]
            lines += [f"  {b['address']}  {b['name']}" for b in info["bonded"]] or ["  (nao listados neste firmware)"]
            lines += ["", "Dispositivos de entrada (o controle conectado aparece como Bluetooth):"]
            lines += [f"  [{d['bus'] or '?':10}] {d['name']}  ({d['sources']})" for d in inp if d["name"]]
            lines += ["", f"Eventos de desconexao/timeout BT no log atual (desde ~{first}): {len(events)}"]
            lines += ["  " + e[:200] for e in events[-40:]]
            lines += ["", f"Dump completo salvo em {path}", "", BT_PHYSICAL_CHECKLIST]
            return "\n".join(lines)
        self.bg(work, lambda t: self._show(self.bt_text, t))


BT_PHYSICAL_CHECKLIST = """\
O que o software consegue mostrar: Bluetooth ligado, controle pareado/conectado, eventos de desconexao
recentes no logcat (o buffer cobre so as ultimas horas), apps que travam e se o controle aparece como
dispositivo de entrada.

O que depende de teste fisico (o software nao mede):
  1. Posicao: o Stick atras da TV fica cercado por metal e pela placa da TV. Use o cabo extensor HDMI
     para afastar o Stick alguns centimetros do painel e teste de novo.
  2. Pilhas: troque por pilhas novas (tensao baixa causa atrasos e quedas antes de o controle parar).
  3. Interferencia 2,4 GHz: roteador, HD/pendrive USB 3.0 na TV, forno de micro-ondas, Wi-Fi 2,4 GHz no
     mesmo canal. Se possivel, ligue o Stick no Wi-Fi de 5 GHz.
  4. Distancia/linha de visada: teste a 1 m e a 4 m; se so falha longe, o problema e de sinal.
  5. Alimentacao: use a fonte original na tomada, nao a USB da TV (subtensao causa instabilidade).
  6. Compare: o controle pelo app Google TV no celular ou por este painel funciona quando o fisico falha?
     Se sim, o problema e o enlace BT do controle, nao o sistema.
Re-parear o controle original so com sua autorizacao (Configuracoes > Controles e acessorios).
"""


class ConnectWizard(tk.Toplevel):
    """Assistente de primeira conexao: instrui o que fazer na TV, procura sozinho e conecta."""

    TV_STEPS = ("Faca isto UMA VEZ, usando o controle da TV:\n\n"
                "1.  Configuracoes (engrenagem)  >  Preferencias do dispositivo  >  Sobre\n"
                "2.  Desca ate \"Build\" e aperte OK 7 vezes, ate aparecer \"Agora voce e um desenvolvedor\".\n"
                "3.  Volte uma tela  >  Opcoes do desenvolvedor  >  ative \"Depuracao USB\".\n"
                "     (Se existir \"Depuracao sem fio\", ative tambem.)\n\n"
                "Pronto? Deixe a TV ligada e clique no botao abaixo.")

    def __init__(self, app: "App") -> None:
        super().__init__(app)
        self.app = app
        self.title("Conectar a TV")
        self.geometry("620x560")
        self.transient(app)
        self.found: list[tuple[str, int, str]] = []
        ttk.Label(self, text="Vamos conectar o Mi TV Stick", font=("Segoe UI", 15, "bold")).pack(pady=(14, 6))
        ttk.Label(self, text=self.TV_STEPS, justify="left", font=("Segoe UI", 10), wraplength=580).pack(padx=18, anchor="w")
        self.search_btn = ttk.Button(self, text="Procurar minha TV", style="Big.TButton", command=self.search)
        self.search_btn.pack(pady=12)
        self.msg = tk.StringVar()
        ttk.Label(self, textvariable=self.msg, font=("Segoe UI", 10, "bold"), wraplength=580, justify="center").pack(padx=18)
        self.choices = tk.Listbox(self, height=4)
        self.choose_btn = ttk.Button(self, text="Conectar nesta", command=self.connect_selected)
        manual = ttk.LabelFrame(self, text="Nao encontrou? Digite o IP que aparece na TV", padding=8)
        manual.pack(side="bottom", fill="x", padx=14, pady=10)
        ttk.Label(manual, text="Na TV: Configuracoes > Preferencias do dispositivo > Sobre > Status > Endereco IP",
                  foreground="gray").pack(anchor="w")
        row = ttk.Frame(manual)
        row.pack(fill="x", pady=4)
        self.ip = tk.StringVar()
        ttk.Entry(row, textvariable=self.ip, width=18).pack(side="left")
        ttk.Button(row, text="Conectar", command=lambda: self.connect(self.ip.get().strip(), 5555)).pack(side="left", padx=6)
        ttk.Button(row, text="Minha TV pede codigo de pareamento", command=app.do_pair).pack(side="right")

    def search(self) -> None:
        self.search_btn.configure(state="disabled")
        self.msg.set("Procurando a TV na sua rede (cerca de 10 segundos)...")
        self.app.bg(lambda: discover_devices(self.app.client, sweep=True), self.search_done)

    def search_done(self, found: list[tuple[str, int, str]]) -> None:
        self.search_btn.configure(state="normal")
        if not self.winfo_exists():
            return
        uniq: dict[str, tuple[str, int, str]] = {}
        for ip, port, src in found:  # prefere a porta 5555 (fixa) a portas de depuracao sem fio
            if ip not in uniq or port == 5555:
                uniq[ip] = (ip, port, src)
        self.found = list(uniq.values())
        if not self.found:
            self.msg.set("Nao encontrei nenhuma TV com a depuracao ativa.\nConfira os passos acima e se o PC e a TV "
                         "estao no mesmo Wi-Fi/roteador. Ou digite o IP da TV la embaixo.")
        elif len(self.found) == 1:
            self.connect(self.found[0][0], self.found[0][1])
        else:
            self.msg.set("Encontrei mais de um aparelho. Escolha a TV (compare com o IP mostrado nela):")
            self.choices.delete(0, "end")
            for ip, port, src in self.found:
                self.choices.insert("end", f"{ip}:{port}   ({src})")
            self.choices.pack(padx=18, fill="x")
            self.choose_btn.pack(pady=4)

    def connect_selected(self) -> None:
        sel = self.choices.curselection()
        if sel:
            ip, port, _ = self.found[sel[0]]
            self.connect(ip, port)

    def connect(self, ip: str, port: int) -> None:
        if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip or ""):
            self.msg.set("IP invalido. Exemplo: 192.168.0.25")
            return
        self.app.ip_var.set(ip)
        self.app.port_var.set(str(port))
        self.app.connect_failure = None
        self.app.do_connect()
        self.msg.set(f"Conectando a {ip}...\n\nOLHE PARA A TV: se aparecer \"Permitir depuracao USB?\", marque "
                     "\"Sempre permitir deste computador\" e escolha OK.")
        self._started = time.time()
        self.after(1000, self.wait_connected)

    def wait_connected(self) -> None:
        if not self.winfo_exists():
            return
        st = self.app.last_state
        if self.app.connect_failure:
            self.msg.set(self.app.connect_failure)
            self.search_btn.configure(text="Procurar minha TV", state="normal", command=self.search)
            return
        if st == "device":
            self.msg.set("Conectado! Agora voce controla a TV pelo computador.")
            self.search_btn.configure(text="Comecar", state="normal", command=self.finish)
            return
        if time.time() - self._started > 90:
            self.msg.set("Nao consegui concluir a conexao. Verifique se a depuracao esta ativa e se voce aceitou "
                         "o aviso na TV, depois tente de novo.")
            return
        self.after(1000, self.wait_connected)

    def finish(self) -> None:
        self.app.nb.select(self.app.control_tab)
        self.destroy()


def scrolled_tree(parent, cols, titles, widths, height: int = 10) -> ttk.Treeview:
    box = ttk.Frame(parent)
    box.pack(fill="both", expand=True, pady=6)
    tree = ttk.Treeview(box, columns=cols, show="headings", height=height)
    for c, t, w in zip(cols, titles, widths):
        tree.heading(c, text=t)
        tree.column(c, width=w, minwidth=40, anchor="w", stretch=False)
    ys = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    xs = ttk.Scrollbar(box, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
    tree.grid(row=0, column=0, sticky="nsew")
    ys.grid(row=0, column=1, sticky="ns")
    xs.grid(row=1, column=0, sticky="ew")
    box.rowconfigure(0, weight=1)
    box.columnconfigure(0, weight=1)
    return tree


def tcp_open(ip: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def local_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # nao envia pacotes; so escolhe a interface de saida
            return s.getsockname()[0]
    except OSError:
        return None


def arp_neighbors() -> list[str]:
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=10,
                             creationflags=CREATE_NO_WINDOW).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    ips = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b\s+([0-9a-fA-F]{2}[-:](?:[0-9a-fA-F]{2}[-:]){4}[0-9a-fA-F]{2})", out)
    return sorted({ip for ip, mac in ips if not ip.endswith(".255") and not mac.lower().startswith(("ff", "01-00-5e"))})


def discover_devices(client: AdbClient, sweep: bool = False) -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []
    r = client.run("mdns", "services", use_serial=False, timeout=10)
    for m in re.finditer(r"_adb(-tls-(?:connect|pairing))?\._tcp\.?\s+(\d+\.\d+\.\d+\.\d+):(\d+)", r.out):
        found.append((m.group(2), int(m.group(3)), f"mDNS {m.group(1) or '_adb'}"))
    me = local_ipv4()
    targets = set(arp_neighbors())
    if me:
        prefix = me.rsplit(".", 1)[0] + "."
        targets = {t for t in targets if t.startswith(prefix) and t != me}
        if sweep:
            targets |= {f"{prefix}{i}" for i in range(1, 255) if f"{prefix}{i}" != me}
    with ThreadPoolExecutor(max_workers=48) as ex:
        for ip, ok in zip(sorted(targets), ex.map(lambda ip: tcp_open(ip, 5555), sorted(targets))):
            if ok:
                found.append((ip, 5555, "TCP 5555 aberta"))
    return found


def compare_metrics(a: dict, b: dict, la: str = "antes", lb: str = "depois") -> str:
    def mb(v):
        return (v or 0) / 1024

    rows = [("RAM disponivel (MB)", mb(a["mem_available_kb"]), mb(b["mem_available_kb"])),
            ("Swap em uso (MB)", mb((a["swap_total_kb"] or 0) - (a["swap_free_kb"] or 0)),
             mb((b["swap_total_kb"] or 0) - (b["swap_free_kb"] or 0))),
            ("Processos", a["processos"], b["processos"]),
            ("Pacotes ativos", a["pacotes_ativos"], b["pacotes_ativos"]),
            ("Load avg (1 min)", float(a["loadavg"].split()[0]) if a.get("loadavg") else 0,
             float(b["loadavg"].split()[0]) if b.get("loadavg") else 0)]
    out = [f"Comparacao: {la}  ->  {lb}", "", f"{'Metrica':24}{'Antes':>12}{'Depois':>12}{'Diferenca':>12}"]
    out += [f"{n:24}{x:12.1f}{y:12.1f}{y - x:+12.1f}" for n, x, y in rows]
    out += ["", f"Uptime antes: {a.get('uptime')}", f"Uptime depois: {b.get('uptime')}", "",
            "Atencao: medidas pontuais variam muito. Compare coletas com tempo de uso parecido (ex.: 10 min apos",
            "ligar, sem app aberto). Diferencas menores que ~50 MB de RAM nao sao conclusivas."]
    return "\n".join(out)


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
