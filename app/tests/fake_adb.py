"""ADB SIMULADO para testes automatizados do codigo (NAO representa dados reais do seu aparelho).
Guarda estado (pacotes desativados, settings) em $FAKE_ADB_STATE para validar desativar/reverter."""
import json, os, sys

STATE = os.environ.get("FAKE_ADB_STATE", "fake_adb_state.json")
SYS = ["android", "com.android.bluetooth", "com.android.tv.settings", "com.google.android.gms", "com.android.vending",
       "com.google.android.tvlauncher", "com.google.android.apps.mediashell", "com.google.android.backdrop",
       "com.google.android.katniss", "com.google.android.youtube.tv", "com.droidlogic.tvinput", "com.xiaomi.mitv.example", "com.mitv.tvhome.atv",
       "com.mitv.dream", "com.miui.tv.analytics", "com.google.android.videos", "com.google.android.tvrecommendations",
       "com.mi.bluetooth", "xiaomi.tvservice", "com.xiaomi.mitv.updateservice", "com.google.android.inputmethod.latin",
       "com.android.vpndialogs", "com.google.android.overlay.modules.ext.services", "com.android.printspooler"]
THIRD = ["com.netflix.ninja", "com.amazon.amazonvideo.livingroom", "ch.protonvpn.android", "com.spotify.tv.android"]

def load():
    try: return json.load(open(STATE))
    except Exception: return {"disabled": [], "settings": {"window_animation_scale": "1.0"}, "connected": False}

def save(s): json.dump(s, open(STATE, "w"))

def pm_list(flag, st):
    allp = SYS + THIRD
    sel = {"-s": SYS, "-3": THIRD, "-d": st["disabled"], "-e": [p for p in allp if p not in st["disabled"]]}.get(flag, allp)
    return "\n".join("package:" + p for p in sel)

def shell(cmd, st):
    if cmd.startswith("getprop "):
        return {"ro.product.manufacturer": "SIMULADO", "ro.product.model": "FAKE-STICK", "ro.build.version.release": "11",
                "ro.build.version.sdk": "30", "ro.build.display.id": "FAKE.BUILD"}.get(cmd.split()[1], "")
    if cmd == "cat /proc/meminfo":
        return "MemTotal:        1950000 kB\nMemFree:          100000 kB\nMemAvailable:     700000 kB\nSwapTotal:        500000 kB\nSwapFree:         400000 kB"
    if cmd.startswith("df"):
        return "Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/block/dm-5 5000000 3000000 2000000  60% /data"
    if cmd.startswith("dumpsys meminfo"):
        return "Applications Memory Usage (in Kilobytes):\n\nTotal PSS by process:\n    185,234K: system (pid 512)\n    120,000K: com.google.android.katniss (pid 900)\n     40,000K: com.google.android.katniss:interactor (pid 901)\n     30,500K: com.google.android.backdrop (pid 950)\n\nTotal PSS by OOM adjustment:\n"
    if cmd.startswith("dumpsys usagestats"):
        return '        package=com.netflix.ninja totalTimeUsed="01:00" lastTimeUsed="2026-11-12 21:00:00"\n        package=com.google.android.backdrop totalTimeUsed="00:00" lastTimeUsed="1970-01-01 00:00:00"'
    if cmd.startswith("pm list packages"):
        parts = cmd.split(); return pm_list(parts[3] if len(parts) > 3 else "", st)
    if cmd.startswith("pm disable-user --user 0 "):
        p = cmd.split()[-1]; st["disabled"] = sorted(set(st["disabled"]) | {p}); save(st)
        return f"Package {p} new state: disabled-user"
    if cmd.startswith("pm enable"):
        p = cmd.split()[-1]; st["disabled"] = [x for x in st["disabled"] if x != p]; save(st)
        return f"Package {p} new state: enabled"
    if cmd.startswith("settings get global "):
        return st["settings"].get(cmd.split()[-1], "null")
    if cmd.startswith("settings put global "):
        _, _, _, k, v = cmd.split(); st["settings"][k] = v; save(st); return ""
    if cmd.startswith("settings delete global "):
        st["settings"].pop(cmd.split()[-1], None); save(st); return "Deleted 1 rows"
    if cmd == "cat /proc/loadavg": return "1.20 0.90 0.70 2/800 4000"
    if cmd == "uptime": return " 20:00:00 up 1 day,  2:00,  0 users,  load average: 1.20, 0.90, 0.70"
    if cmd.startswith("ps -A"): return "PID\n1\n2\n3"
    if cmd.startswith("cmd package resolve-activity") and "HOME" in cmd:
        return "priority=0 preferredOrder=0 match=0x108000 specificIndex=-1 isDefault=true\n" + st.get("home", "com.google.android.tvlauncher") + "/.MainActivity"
    if cmd.startswith("cmd package query-activities") and "HOME" in cmd:
        homes = [h for h in ["com.google.android.tvlauncher", "com.mitv.tvhome.atv", "com.android.tv.settings"] if h not in st["disabled"]]
        return "\n".join(h + "/.Home" for h in homes)
    if cmd.startswith("cmd package query-activities"):
        return "com.netflix.ninja/.MainActivity\ncom.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.ShellActivity"
    if cmd.startswith("monkey -p"):
        p = cmd.split()[2]
        return "Events injected: 1" if p in SYS + THIRD else "** No activities found to run, monkey aborted."
    if cmd.startswith("dumpsys bluetooth_manager"):
        return "Bluetooth Status\n  enabled: true\n  state: ON\n  address: XX:XX:XX:XX:12:34\n  name: MiTV-SIMULADO\n\nBonded devices:\n  XX:XX:XX:XX:AB:CD [ DUAL ] Xiaomi RC\n\n"
    if cmd.startswith("dumpsys input"):
        return "Input Reader State:\n  Device 5: Xiaomi RC\n    Generation: 12\n    Identifier: bus=0x0005, vendor=0x2717, product=0x32b9\n    Sources: 0x00000101\n  Device 3: hdmi_cec_key\n    Identifier: bus=0x0000\n    Sources: 0x00000101\n"
    if cmd.startswith("logcat"):
        return "11-13 18:00:01.000 I/bt_btif (1000): btif_hh_upstreams_evt: HID disconnect, reason=0x08 supervision timeout\n11-13 18:00:05.000 I/ActivityManager(500): Start proc"
    if cmd.startswith("input "): return ""
    return f"(simulado) {cmd}"

def main(argv):
    st = load()
    if argv[:1] == ["-s"]: argv = argv[2:]
    if not argv: return 1
    c = argv[0]
    if c == "start-server": return 0
    if c == "connect": st["connected"] = True; save(st); print(f"connected to {argv[1]}"); return 0
    if c == "disconnect": st["connected"] = False; save(st); print(f"disconnected {argv[1] if len(argv)>1 else ''}"); return 0
    if c == "get-state":
        if st["connected"]: print("device"); return 0
        print("error: device not found", file=sys.stderr); return 1
    if c == "devices": print("List of devices attached\n192.0.2.10:5555 device product:FAKE model:FAKE-STICK"); return 0
    if c == "mdns": print("List of discovered mdns services"); return 0
    if c == "pair": print("Successfully paired to " + argv[1]); return 0
    if c == "version": print("Android Debug Bridge version 1.0.41 (simulado)"); return 0
    if c == "shell":
        if len(argv) == 1:
            with open(STATE + ".keys", "a") as f:
                for line in sys.stdin: f.write(line); f.flush()
            return 0
        print(shell(" ".join(argv[1:]), st)); return 0
    print("unknown command", file=sys.stderr); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
