"""Testes das partes puras (parsers, classificacao, historico). Rode: py -3 -m unittest discover -s app/tests"""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import parsers as P
from knowledge import KnowledgeBase
from history import History
from adb_client import escape_input_text, is_valid_package
import netdiag as N


class Parsers(unittest.TestCase):
    def test_meminfo(self):
        m = P.parse_meminfo("MemTotal:  1950000 kB\nMemAvailable:   700000 kB\nActive(anon): 5 kB")
        self.assertEqual(m["MemTotal"], 1950000); self.assertEqual(m["MemAvailable"], 700000); self.assertEqual(m["Active(anon)"], 5)

    def test_df(self):
        r = P.parse_df("Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-5 5000000 3000000 2000000 60% /data")
        self.assertEqual(r[0]["mount"], "/data"); self.assertEqual(r[0]["use"], "60%")

    def test_packages(self):
        self.assertEqual(P.parse_packages("package:b.c\npackage:/system/app/X.apk=a.b\njunk"), ["a.b", "b.c"])

    def test_pss_merges_subprocesses_and_stops(self):
        t = "Total PSS by process:\n  120,000K: com.a (pid 1)\n   40,000K: com.a:svc (pid 2)\n    1,000K: com.b (pid 3 / activities)\n\nTotal PSS by OOM adjustment:\n  999K: Native\n"
        self.assertEqual(P.parse_pss_by_process(t), {"com.a": 160000, "com.b": 1000})

    def test_rss_android13(self):
        self.assertEqual(P.parse_pss_by_process("Total RSS by process:\n  10K: x.y (pid 1)\n"), {"x.y": 10})

    def test_usagestats(self):
        t = 'package=a.b lastTimeUsed="2026-01-01 10:00:00"\npackage=a.b lastTimeUsed="2026-02-01 10:00:00"\npackage=c.d lastTimeUsed="1970-01-01 00:00:00"'
        self.assertEqual(P.parse_usagestats_last_used(t), {"a.b": "2026-02-01 10:00:00"})

    def test_bluetooth(self):
        b = P.parse_bluetooth("  enabled: true\n  state: ON\n  name: TV\n\nBonded devices:\n  XX:XX:XX:XX:AB:CD [ DUAL ] Xiaomi RC\n\n")
        self.assertTrue(b["enabled"]); self.assertEqual(b["state"], "ON"); self.assertEqual(b["bonded"][0]["name"], "Xiaomi RC")

    def test_input_devices(self):
        d = P.parse_input_devices("  Device 5: Xiaomi RC\n    Identifier: bus=0x0005, vendor=0x2717\n    Sources: 0x101\n  Device 3: cec\n    Identifier: bus=0x0000\n")
        self.assertEqual(d[0]["bus"], "Bluetooth"); self.assertEqual(d[1]["bus"], "Interno")

    def test_bt_disconnects(self):
        self.assertEqual(len(P.count_bt_disconnects("bt_btif: HID disconnect\nWifi disconnect\nfoo")), 1)


class DadosReaisMiStick(unittest.TestCase):
    """Saidas reais do aparelho do usuario (firmware 25.9.9.1546)."""
    D = Path(__file__).resolve().parent / "dados_reais"

    def test_prefere_pss_ao_rss(self):
        pss = P.parse_pss_by_process((self.D / "dumpsys-meminfo-trecho.txt").read_text())
        self.assertEqual(pss["com.google.android.tvlauncher"], 253795)   # PSS, nao o RSS 338608
        self.assertEqual(pss["com.google.android.katniss"], 50054 + 39929)  # interactor + search somados
        self.assertNotIn("Native", pss)  # tabela por categoria nao entra

    def test_meminfo_real(self):
        m = P.parse_meminfo((self.D / "proc-meminfo.txt").read_text())
        self.assertEqual((m["MemTotal"], m["MemAvailable"], m["SwapTotal"]), (2038028, 629096, 1019008))

    def test_df_real(self):
        data = [r for r in P.parse_df((self.D / "df.txt").read_text()) if r["mount"] == "/data"]
        self.assertEqual(data[0]["use"], "86%")


class HomeGuard(unittest.TestCase):
    D = "priority=0 preferredOrder=0 match=0x108000 specificIndex=-1 isDefault=true\ncom.google.android.tvlauncher/.MainLauncher"
    ALL = "com.google.android.tvlauncher/.MainLauncher\ncom.mitv.tvhome.atv/.HomeActivity\ncom.android.tv.settings/.FallbackHome"

    def test_patchwall_permitido_quando_nao_e_padrao(self):
        self.assertIsNone(P.home_guard("com.mitv.tvhome.atv", self.D, self.ALL))

    def test_recusa_tela_inicial_padrao(self):
        self.assertIn("PADRAO", P.home_guard("com.google.android.tvlauncher", self.D, self.ALL))

    def test_recusa_unica_tela_inicial(self):
        only = "com.mitv.tvhome.atv/.HomeActivity\ncom.android.tv.settings/.FallbackHome"
        self.assertIn("UNICA", P.home_guard("com.mitv.tvhome.atv", "android/com.android.internal.app.ResolverActivity", only))

    def test_recusa_sem_informacao(self):
        self.assertIsNotNone(P.home_guard("x.y", "No activity found", ""))

    def test_app_comum_nao_afetado(self):
        self.assertIsNone(P.home_guard("com.google.android.katniss", self.D, self.ALL))


class Knowledge(unittest.TestCase):
    kb = KnowledgeBase()

    def test_protected(self):
        for p in ["com.netflix.ninja", "com.google.android.gms", "com.google.android.gms.policy_sidecar_aps", "com.android.bluetooth",
                  "com.google.android.tvlauncher", "com.google.android.apps.mediashell", "com.droidlogic.tvinput",
                  "com.android.vending", "com.google.android.youtube.tv", "android", "com.android.providers.tv", "com.android.wifi.resources"]:
            self.assertTrue(self.kb.is_protected(p), p)
            self.assertEqual(self.kb.classify(p).category, "Essencial", p)

    def test_not_protected(self):
        self.assertEqual(self.kb.classify("com.google.android.backdrop").category, "Candidato")
        self.assertEqual(self.kb.classify("com.google.android.katniss").category, "Opcional")
        self.assertFalse(self.kb.is_protected("androidx.test"))
        self.assertEqual(self.kb.classify("com.xiaomi.algo").category, "Desconhecido")
        self.assertEqual(self.kb.classify("com.mitv.tvhome.atv").category, "Opcional")  # PatchWall
        self.assertTrue(self.kb.is_protected("com.mi.bluetooth"))


class Explicacoes(unittest.TestCase):
    kb = KnowledgeBase()

    def test_nomes_compreensiveis(self):
        self.assertEqual(self.kb.classify("com.google.android.katniss").name, "Assistente de voz do Google")
        self.assertEqual(self.kb.classify("com.mitv.tvhome.atv").name, "PatchWall (Xiaomi)")
        self.assertEqual(self.kb.classify("com.google.android.katniss").recommendation, "Depende do seu uso")

    def test_app_do_usuario(self):
        i = self.kb.classify("com.plexapp.android", third_party=True)
        self.assertEqual((i.category, i.recommendation, i.name), ("Instalado por você", "Decisão sua", "Plexapp"))
        self.assertTrue(self.kb.classify("com.netflix.ninja", third_party=True).protected)  # streaming continua protegido

    def test_regras_por_familia(self):
        self.assertEqual(self.kb.classify("com.droidlogic.hdmiin").name, "Componente do chip Amlogic")
        self.assertEqual(self.kb.classify("com.droidlogic.hdmiin").category, "Essencial")
        self.assertEqual(self.kb.classify("com.google.android.overlay.modules.ext.services").category, "Essencial")
        x = self.kb.classify("com.xiaomi.mitv.algumacoisa")
        self.assertEqual((x.name, x.category), ("Componente da Xiaomi", "Desconhecido"))

    def test_todos_tem_campos(self):
        for pkg in self.kb.packages:
            i = self.kb.classify(pkg)
            self.assertTrue(i.name and i.function and i.effect and i.recommendation, pkg)


class Misc(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(escape_input_text("a b&c'"), "a%sb\\&c\\'")

    def test_valid_pkg(self):
        self.assertTrue(is_valid_package("com.a.b")); self.assertFalse(is_valid_package("com.a;rm -rf /")); self.assertFalse(is_valid_package("x"))

    def test_history(self):
        with tempfile.TemporaryDirectory() as d:
            h = History(Path(d) / "h.json")
            e = h.add("pacote", "a.b", "enabled", "disabled-user", ["pm", "enable", "a.b"], "ok")
            h.add("configuracao", "k", "1.0", "0.5", ["settings", "put", "global", "k", "1.0"], "ok")
            h.mark_reverted(e["id"], "ok")
            data = h.load()
            self.assertEqual([x["id"] for x in data], [1, 2]); self.assertTrue(data[0]["revertido"]); self.assertFalse(data[1]["revertido"])

    def test_history_concurrent_writes_not_lost(self):
        import threading
        with tempfile.TemporaryDirectory() as d:
            h = History(Path(d) / "h.json")
            ts = [threading.Thread(target=lambda i=i: h.add("pacote", f"a.p{i}", "enabled", "disabled-user", ["pm", "enable", f"a.p{i}"], "ok")) for i in range(40)]
            [t.start() for t in ts]; [t.join() for t in ts]
            data = h.load()
            self.assertEqual(len(data), 40); self.assertEqual(sorted(e["id"] for e in data), list(range(1, 41)))

    def test_history_reads_powershell_bom_single_object(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "h.json"; p.write_text('﻿{"id": 7, "reverter": ["pm","enable","x.y"]}', encoding="utf-8")
            self.assertEqual(History(p).load()[0]["id"], 7)


class NetDiag(unittest.TestCase):
    def test_open(self):
        t, p = N.diagnose("192.168.1.50", 5555, "open", True, "192.168.1.10", [])
        self.assertIn("Tudo certo", t); self.assertIsNone(p)

    def test_refused_means_debug_off(self):
        t, _ = N.diagnose("192.168.1.50", 5555, "refused", True, "192.168.1.10", [])
        self.assertIn("NAO esta ativa", t)

    def test_timeout_with_ping_means_debug_off(self):
        self.assertIn("NAO esta ativa", N.diagnose("192.168.1.50", 5555, "timeout", True, "192.168.1.10", [])[0])

    def test_timeout_no_ping_means_off_or_wrong_ip(self):
        t, _ = N.diagnose("192.168.1.50", 5555, "timeout", False, "192.168.1.10", [])
        self.assertIn("Nenhuma resposta", t); self.assertNotIn("DIFERENTES", t)

    def test_wireless_debugging_port_suggested(self):
        t, p = N.diagnose("192.168.1.50", 5555, "refused", True, "192.168.1.10", [37215])
        self.assertEqual(p, 37215); self.assertIn("Depuracao sem fio", t)

    def test_different_network_warning(self):
        self.assertIn("DIFERENTES", N.diagnose("192.168.1.50", 5555, "timeout", False, "10.0.0.15", [])[0])
        self.assertIsNone(N.same_network_hint("192.168.2.4", "192.168.1.50"))  # Deco usa /22

    def test_mdns_ports(self):
        out = "List of discovered mdns services\nadb-123\t_adb-tls-connect._tcp\t192.168.1.50:37215\nadb-9\t_adb-tls-connect._tcp\t192.168.1.99:4000"
        self.assertEqual(N.mdns_ports(out, "192.168.1.50"), [37215])

    def test_probe_refused_and_open(self):
        import socket
        srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
        self.assertEqual(N.probe_tcp("127.0.0.1", port), "open"); srv.close()
        self.assertEqual(N.probe_tcp("127.0.0.1", port), "refused")


if __name__ == "__main__":
    unittest.main()
