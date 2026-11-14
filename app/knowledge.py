"""Classificacao e explicacao de pacotes a partir de data/pacotes-conhecidos.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pacotes-conhecidos.json"

ESSENCIAL, OPCIONAL, CANDIDATO, SEU_APP, DESCONHECIDO = "Essencial", "Opcional", "Candidato", "Instalado por você", "Desconhecido"

RECOMENDACAO = {
    ESSENCIAL: "Manter (necessário)",
    OPCIONAL: "Depende do seu uso",
    CANDIDATO: "Pode desativar se não usa",
    SEU_APP: "Decisão sua",
    DESCONHECIDO: "Não mexer (sem informação)",
}
ORDEM = {CANDIDATO: 0, OPCIONAL: 1, SEU_APP: 2, DESCONHECIDO: 3, ESSENCIAL: 4}


@dataclass
class PkgInfo:
    package: str
    category: str
    name: str          # nome compreensivel
    function: str      # o que e
    effect: str        # o que acontece se desativar
    impact: str        # impacto no desempenho
    protected: bool

    @property
    def recommendation(self) -> str:
        return RECOMENDACAO.get(self.category, "")

    @property
    def revert(self) -> str:
        return f"pm enable --user 0 {self.package}"

    @property
    def risk(self) -> str:  # compatibilidade com versoes anteriores
        return self.effect


def guess_name(pkg: str) -> str:
    """Nome legivel a partir do pacote: ch.protonvpn.android -> Protonvpn."""
    skip = {"com", "br", "org", "net", "tv", "android", "app", "apps", "atv", "androidtv", "mobile", "ch", "de", "io", "co", "uk"}
    parts = [p for p in pkg.split(".") if p.lower() not in skip]
    return (parts[0] if parts else pkg).replace("_", " ").capitalize()


class KnowledgeBase:
    def __init__(self, path: Path = DB_PATH):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.prefixes: list[str] = data["protegidos_prefixo"]
        self.packages: dict[str, dict] = data["pacotes"]
        self.rules: list[dict] = data.get("regras", [])

    def is_protected(self, pkg: str) -> bool:
        for pre in self.prefixes:
            if pre.endswith("."):
                if pkg.startswith(pre):
                    return True
            elif pkg == pre or pkg.startswith(pre + "."):
                return True
        return self.packages.get(pkg, {}).get("cat") == ESSENCIAL

    def _rule(self, pkg: str) -> dict | None:
        for r in self.rules:
            if ("prefixo" in r and pkg.startswith(r["prefixo"])) or ("contem" in r and r["contem"] in pkg):
                return r
        return None

    def classify(self, pkg: str, third_party: bool = False) -> PkgInfo:
        prot = self.is_protected(pkg)
        d = self.packages.get(pkg)
        if d:
            return PkgInfo(pkg, ESSENCIAL if prot else d["cat"], d["nome"], d["funcao"], d["efeito"], d.get("impacto", "-"), prot)
        if third_party and not prot:
            return PkgInfo(pkg, SEU_APP, guess_name(pkg), "App que você (ou alguém) instalou pela Play Store.",
                           "O app some até ser reativado. Se não usa, pode também desinstalar em Configurações > Apps.", "?", False)
        r = self._rule(pkg)
        if r:
            cat = ESSENCIAL if prot else r["cat"]
            return PkgInfo(pkg, cat, r["nome"], r["funcao"], r["efeito"], "-", prot)
        if prot:
            return PkgInfo(pkg, ESSENCIAL, "Componente protegido do sistema", "Parte do sistema, do Google ou de streaming.", "Protegido: não desativar.", "-", True)
        return PkgInfo(pkg, DESCONHECIDO, guess_name(pkg), "Função não identificada.", "Desconhecido — não mexa sem pesquisar.", "?", False)

    def label(self, pkg: str, third_party: bool = False) -> str:
        """'Nome amigavel (pacote)' para listas."""
        return f"{self.classify(pkg, third_party).name}  ({pkg})"
