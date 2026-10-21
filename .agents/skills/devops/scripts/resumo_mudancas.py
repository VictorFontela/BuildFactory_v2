"""Junta o que a capacidade mudou, para o DevOps montar o pacote do humano.

Uso (a partir da raiz do repositório):
    python .agents/skills/devops/scripts/resumo_mudancas.py --capacidade <nome> [--saida <arquivo.json>]

Lê a linha de base (`.agents/state/<capacidade>/baseline-suite.json`, gravada no
começo) e o histórico de eventos, e consulta o git. Devolve em JSON:
  - base e HEAD, e os commits entre eles, com o papel de cada um;
  - os arquivos alterados, com linhas a mais e a menos;
  - por passo: descrição, quem aprovou e as voltas;
  - o que pede atenção na subida: dependência, migração, configuração, CI;
  - o comando para voltar atrás.
Não muda nada no repositório.

Saída 0: ok. 2: capacidade sem linha de base, sem histórico, uso errado ou falha do git.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ATENCAO = [
    ("dependencia", re.compile(r"(^|/)(requirements[^/]*\.txt|pyproject\.toml|poetry\.lock|uv\.lock|Pipfile(\.lock)?|"
                               r"package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|go\.mod|Cargo\.toml)$")),
    ("migracao", re.compile(r"(^|/)(migrations?|alembic|migracoes)/")),
    ("configuracao", re.compile(r"(^|/)(\.env[^/]*|[^/]*\.ya?ml|[^/]*\.toml|[^/]*\.ini|settings[^/]*\.py|config[^/]*)$")),
    ("infra", re.compile(r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*|\.gitlab-ci\.yml|\.github/|infra/|k8s/|helm/|terraform/)")),
]
PAPEL = re.compile(r"^Papel: *(\w+) *$", re.M)


class Uso(Exception):
    pass


def git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise Uso(f"git {' '.join(args)} falhou: {r.stderr.strip()}")
    return r.stdout


def eventos(pasta):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((pasta / "eventos").glob("*.json"))]


def resumir(raiz, capacidade):
    raiz = Path(raiz).resolve()
    pasta = raiz / ".agents" / "state" / capacidade
    base_p = pasta / "baseline-suite.json"
    if not base_p.is_file():
        raise Uso(f"sem linha de base em {base_p.relative_to(raiz)}: o Orchestrator grava no começo da capacidade")
    base = json.loads(base_p.read_text(encoding="utf-8"))["commit"]
    evs = eventos(pasta)
    if not evs:
        raise Uso(f"sem histórico em {(pasta / 'eventos').relative_to(raiz)}")
    head = git(raiz, "rev-parse", "--short=12", "HEAD").strip()
    commits = []
    for linha in git(raiz, "log", "--reverse", "--format=%h%x00%s%x00%B%x1e", f"{base}..HEAD").split("\x1e"):
        if not linha.strip():
            continue
        h, assunto, corpo = linha.strip("\n").split("\x00", 2)
        papeis = PAPEL.findall(corpo)
        commits.append({"commit": h, "assunto": assunto, "papel": papeis[0] if papeis else ("Tests" if assunto.startswith("test") else None)})
    arquivos = []
    for linha in git(raiz, "diff", "--numstat", f"{base}..HEAD").splitlines():
        mais, menos, caminho = linha.split("\t", 2)
        arquivos.append({"arquivo": caminho, "mais": mais, "menos": menos})
    atencao = {nome: [a["arquivo"] for a in arquivos if rx.search(a["arquivo"])] for nome, rx in ATENCAO}
    spec = next((e for e in reversed(evs) if e["tipo"] == "spec_pronta"), {"passos": []})
    passos = []
    for p in spec["passos"]:
        aprov = [e["papel"] for e in evs if e["tipo"] == "aprovado" and e["passo"] == p["id"]]
        voltas = [{"reprovou": e["reprovou"], "motivo": e["motivo"]} for e in evs if e["tipo"] == "reprovacao" and e["passo"] == p["id"]]
        passos.append({"passo": p["id"], "descricao": p["descricao"], "aprovado_por": aprov, "voltas": voltas})
    sujos = [l for l in git(raiz, "status", "--porcelain").splitlines() if l and not l[3:].startswith(".agents/state/")]
    return {
        "capacidade": capacidade, "pedido": evs[0].get("pedido"), "base": base, "head": head,
        "commits": commits, "arquivos": arquivos, "passos": passos,
        "atencao": {k: v for k, v in atencao.items() if v},
        "mudancas_sem_commit": sujos,
        "voltar_atras": {"sem_push": f"git reset --hard {base}",
                         "depois_do_push": f"git revert --no-edit {base}..{head}"},
        "remoto": bool(git(raiz, "remote").strip()),
    }


def principal(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--capacidade", required=True)
    p.add_argument("--saida")
    p.add_argument("--raiz", default=".")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        r = resumir(a.raiz, a.capacidade)
    except Uso as e:
        print(str(e), file=sys.stderr)
        return 2
    texto = json.dumps(r, ensure_ascii=False, indent=2)
    if a.saida:
        Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
        Path(a.saida).write_text(texto + "\n", encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
