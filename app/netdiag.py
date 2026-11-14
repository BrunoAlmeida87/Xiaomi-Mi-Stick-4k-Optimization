"""Diagnostico de conexao em linguagem simples (sem Tkinter, testavel)."""
from __future__ import annotations

import os
import re
import socket
import subprocess

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def probe_tcp(ip: str, port: int, timeout: float = 2.0) -> str:
    """'open' | 'refused' (aparelho existe, porta fechada) | 'timeout' (sem resposta) | 'unreachable'."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return "open"
    except ConnectionRefusedError:
        return "refused"
    except socket.timeout:
        return "timeout"
    except OSError as e:
        if getattr(e, "winerror", None) == 10061 or e.errno in (111, 10061):
            return "refused"
        return "unreachable"


def ping_host(ip: str) -> bool | None:
    """True/False conforme resposta ao ping; None se o ping nao puder ser executado."""
    args = ["ping", "-n", "2", "-w", "1000", ip] if os.name == "nt" else ["ping", "-c", "2", "-W", "1", ip]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=8, creationflags=CREATE_NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return None
    # No Windows o codigo de saida pode ser 0 mesmo com "Host de destino inacessivel": exige TTL na resposta.
    return r.returncode == 0 and "ttl" in r.stdout.lower()


def local_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # nao envia pacotes; so escolhe a interface de saida
            return s.getsockname()[0]
    except OSError:
        return None


def mdns_ports(mdns_output: str, ip: str) -> list[int]:
    """Portas de 'Depuracao sem fio' anunciadas por este IP (adb mdns services)."""
    ports = []
    for m in re.finditer(r"_adb-tls-connect\._tcp\.?\s+(\d+\.\d+\.\d+\.\d+):(\d+)", mdns_output):
        if m.group(1) == ip:
            ports.append(int(m.group(2)))
    return ports


def same_network_hint(pc_ip: str | None, tv_ip: str) -> str | None:
    if not pc_ip:
        return None
    a, b = pc_ip.split("."), tv_ip.split(".")
    if a[:2] != b[:2] or abs(int(a[2]) - int(b[2])) > 3:
        return (f"ATENCAO: este PC esta no endereco {pc_ip} e a TV em {tv_ip}. Parecem redes DIFERENTES "
                "(ex.: PC ligado no roteador da operadora e TV no roteador mesh/Deco, ou TV na rede de convidados). "
                "Coloque os dois na mesma rede.")
    return None


def diagnose(ip: str, port: int, tcp: str, ping: bool | None, pc_ip: str | None, wireless_ports: list[int]) -> tuple[str, int | None]:
    """Recebe os resultados das sondagens e devolve (explicacao, porta_sugerida)."""
    lines = [f"Teste de conexao com {ip}:{port}",
             f"  Este PC: {pc_ip or 'desconhecido'}",
             f"  Ping na TV: {'respondeu' if ping else 'sem resposta' if ping is False else 'nao testado'}",
             f"  Porta {port}: " + {"open": "ABERTA", "refused": "recusada (a TV respondeu, mas a porta esta fechada)",
                                    "timeout": "sem resposta", "unreachable": "endereco inalcancavel"}[tcp], ""]
    suggested = None
    hint = same_network_hint(pc_ip, ip)
    if tcp == "open":
        lines.append("Tudo certo com a rede. Se a conexao nao concluir, aceite o aviso 'Permitir depuracao USB?' na TV.")
    elif wireless_ports:
        suggested = wireless_ports[0]
        lines.append(f"Sua TV usa 'Depuracao sem fio' na porta {suggested} (nao na {port}).")
        lines.append("Clique em 'Minha TV pede codigo de pareamento' (ou 'Parear'), use o IP:porta e o codigo mostrados "
                     f"na TV em 'Parear dispositivo com codigo', e depois conecte na porta {suggested}.")
    elif tcp == "refused" or (tcp == "timeout" and ping):
        lines.append("A TV esta na rede, mas a depuracao pela rede NAO esta ativa nesta porta. Na TV:")
        lines.append("  Configuracoes > Preferencias do dispositivo > Opcoes do desenvolvedor:")
        lines.append("  1) confirme que 'Depuracao USB' esta ATIVADA (desative e ative de novo, se ja estava);")
        lines.append("  2) se existir 'Depuracao sem fio', ative e use o botao de pareamento com codigo.")
        lines.append("  Se nao existir 'Opcoes do desenvolvedor': Sobre > aperte OK 7 vezes em 'Build'.")
    else:
        lines.append("Nenhuma resposta desse endereco. Verifique, nesta ordem:")
        lines.append("  1) a TV esta LIGADA e com a tela acesa (o Stick desliga o Wi-Fi quando dorme);")
        lines.append("  2) o IP esta certo: TV > Configuracoes > Preferencias do dispositivo > Sobre > Status;")
        lines.append("  3) o PC e a TV estao no MESMO Wi-Fi/roteador (sem rede de convidados).")
    if hint:
        lines += ["", hint]
    return "\n".join(lines), suggested
