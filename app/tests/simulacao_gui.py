"""Teste de ponta a ponta do painel contra um ADB SIMULADO (fake_adb.py).
Valida o codigo do app (conexao, teclas, diagnostico, desativar/reverter, historico, Bluetooth);
NAO valida o comportamento do seu Mi Stick. Roda numa copia temporaria do projeto.
Uso:  py -3 app\\tests\\simulacao_gui.py
"""
import json, os, shutil, stat, sys, tempfile, time
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
tmp = Path(tempfile.mkdtemp(prefix="xtm-test-"))
proj = tmp / "proj"
shutil.copytree(SRC, proj, ignore=shutil.ignore_patterns("reports", "logs", "__pycache__", "historico.json"))
for d in ("reports", "logs"):
    (proj / d).mkdir(exist_ok=True)
fake = proj / "app" / "tests" / "fake_adb.py"
if os.name == "nt":
    wrapper = tmp / "adb.bat"
    wrapper.write_text(f'@"{sys.executable}" "{fake}" %*\n')
else:
    wrapper = tmp / "adb"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n')
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
os.environ["FAKE_ADB_STATE"] = str(tmp / "state.json")
cfg = json.loads((proj / "config.json").read_text(encoding="utf-8-sig"))
cfg.update(ip="192.0.2.10", port=5555, adb_path=str(wrapper), auto_reconnect=True)
(proj / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

sys.path.insert(0, str(proj / "app"))
import xiaomi_tv_manager as X  # noqa: E402
X.messagebox.askyesno = lambda *a, **k: True
X.tcp_open = lambda *a, **k: True  # o IP de teste (192.0.2.10) nao existe; simula porta 5555 aberta
X.N.probe_tcp = lambda *a, **k: X._SIM_TCP
X._SIM_TCP = "open"
X.N.ping_host = lambda ip: True
X.messagebox.showinfo = X.messagebox.showwarning = X.messagebox.showerror = lambda *a, **k: None

app = X.App()
def pump(cond, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        app.update()
        if cond():
            return True
        time.sleep(0.05)
    return False

results = []
def check(name, ok):
    results.append((name, bool(ok))); print(("PASSOU " if ok else "FALHOU ") + name)

check("conecta e fica 'device'", pump(lambda: app.last_state == "device"))
check("lista de apps carregada", pump(lambda: app.apps_list.size() >= 1))

app.send_key("HOME"); app.send_key("UP"); app.text_var.set("ola mundo"); app.send_text()
keys_file = Path(os.environ["FAKE_ADB_STATE"] + ".keys")
pump(lambda: False, 1.5); app.client.close_key_shell(); pump(lambda: False, 0.5)
sent = keys_file.read_text() if keys_file.exists() else ""
check("teclas pelo shell persistente", "input keyevent 3" in sent and "input keyevent 19" in sent and "input text ola%smundo" in sent)

app.diag_full()
check("coleta completa gera resumo.json", pump(lambda: list((proj / "reports").glob("diagnostico-*/resumo.json")), 60))
time.sleep(1.1); app.diag_full()
pump(lambda: len(list((proj / "reports").glob("diagnostico-*/resumo.json"))) >= 2, 60)
app.diag_compare()
check("comparacao antes/depois", "RAM disponivel" in app.diag_text.get("1.0", "end"))

app.load_packages()
check("pacotes classificados", pump(lambda: len(app.pkg_rows) >= 10, 30))
check("netflix protegido", app.pkg_rows["com.netflix.ninja"]["info"].protected)
check("katniss com RAM somada", app.pkg_rows["com.google.android.katniss"]["ram"] == "156 MB")

app.pkg_tree.selection_set("com.google.android.backdrop") if app.pkg_tree.exists("com.google.android.backdrop") else None
app.disable_selected()
check("backdrop desativado", pump(lambda: app.pkg_rows["com.google.android.backdrop"]["estado"] == "desativado"))
state = json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text())
check("estado no 'aparelho' simulado", "com.google.android.backdrop" in state["disabled"])

app.filter_var.set("Todos"); app._fill_pkg_tree(); app.pkg_tree.selection_set("com.netflix.ninja"); app.disable_selected()
pump(lambda: False, 1.0)
state = json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text())
check("tentativa em pacote protegido recusada", "com.netflix.ninja" not in state["disabled"])

app.pkg_rows.setdefault("com.mitv.tvhome.atv", dict(app.pkg_rows["com.google.android.backdrop"], info=app.kb.classify("com.mitv.tvhome.atv"), estado="ativo"))
app._change_package("com.mitv.tvhome.atv", disable=True)
check("PatchWall desativado (nao e a tela inicial padrao)", pump(lambda: "com.mitv.tvhome.atv" in json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text())["disabled"]))
st_ = json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text()); st_["home"] = "com.google.android.katniss"; Path(os.environ["FAKE_ADB_STATE"]).write_text(json.dumps(st_))
app._change_package("com.google.android.katniss", disable=True)
pump(lambda: False, 1.5)
st_ = json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text())
check("recusa desativar a tela inicial padrao", "com.google.android.katniss" not in st_["disabled"] and "RECUSADO" in app.conn_log.get("1.0", "end"))
st_.pop("home"); Path(os.environ["FAKE_ADB_STATE"]).write_text(json.dumps(st_))

app.set_animations("0.5")
check("animacoes 0.5 aplicadas", pump(lambda: json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text())["settings"].get("animator_duration_scale") == "0.5"))
pump(lambda: any(e["alvo"] == "animator_duration_scale" for e in app.hist.load()))  # espera as 3 escalas gravadas
hist = app.hist.load()
check("historico registra estado anterior", any(e["alvo"] == "window_animation_scale" and e["antes"] == "1.0" for e in hist))

app.revert_all()
def reverted():
    s = json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text())
    return not s["disabled"] and s["settings"].get("window_animation_scale") == "1.0" and "animator_duration_scale" not in s["settings"]
check("reverter tudo restaura estado original", pump(reverted, 30))
check("historico marcado como revertido", pump(lambda: all(e["revertido"] for e in app.hist.load())))

app.bt_analyze()
check("analise Bluetooth", pump(lambda: "Xiaomi RC" in app.bt_text.get("1.0", "end") and "desconexao/timeout BT no log atual" in app.bt_text.get("1.0", "end"), 30))
txt = app.bt_text.get("1.0", "end")
check("controle identificado como Bluetooth", "[Bluetooth ] Xiaomi RC" in txt)

app.launch("com.netflix.ninja")
check("abrir app", pump(lambda: "Aberto: com.netflix.ninja" in app.conn_log.get("1.0", "end")))

Path(os.environ["FAKE_ADB_STATE"]).write_text(json.dumps(dict(json.loads(Path(os.environ["FAKE_ADB_STATE"]).read_text()), connected=False)))
check("detecta queda e reconecta sozinho", pump(lambda: "Reconexao automatica" in app.conn_log.get("1.0", "end"), 40))

# Assistente de primeira conexao (busca na rede simulada encontra a TV)
app.do_disconnect(); pump(lambda: app.last_state != "device", 10)
X.discover_devices = lambda client, sweep=False: [("192.0.2.10", 5555, "TCP 5555 aberta")]
wiz = X.ConnectWizard(app)
wiz.search()
check("assistente encontra e conecta sozinho", pump(lambda: "Conectado!" in wiz.msg.get(), 30))
wiz.finish()
check("assistente leva ao controle remoto", app.nb.select() == str(app.control_tab))

# TV com depuracao desligada: diagnostico claro e sem tentativas infinitas
app.do_disconnect(); pump(lambda: app.last_state != "device", 10)
X._SIM_TCP = "refused"
app.do_connect()
check("diagnostico explica depuracao desativada", pump(lambda: app.connect_failure is not None and "NAO esta ativa" in app.connect_failure, 15))
check("sem reconexao automatica apos falha", not app.want_connected)
X._SIM_TCP = "open"
app.do_connect()
check("conecta de novo apos ativar", pump(lambda: app.last_state == "device", 20))

app.export_revert()
app._on_close()
shutil.rmtree(tmp, ignore_errors=True)
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} verificacoes passaram")
sys.exit(1 if failed else 0)
