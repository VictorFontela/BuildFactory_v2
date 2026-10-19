"""Lê relatórios de teste em JUnit XML (pytest --junitxml, jest-junit, vitest --reporter=junit)."""
import xml.etree.ElementTree as ET
from pathlib import Path


class RelatorioInvalido(Exception):
    pass


def ler_junit(caminho):
    """Devolve a lista de casos: {classe, nome, arquivo, tipo (ok|falha|erro|pulado), msg}."""
    if not Path(caminho).is_file():
        raise RelatorioInvalido(f"o comando não gravou o relatório JUnit em {caminho}")
    try:
        raiz = ET.parse(caminho).getroot()
    except ET.ParseError as e:
        raise RelatorioInvalido(f"relatório JUnit ilegível: {e}")
    casos = []
    for tc in raiz.iter("testcase"):
        tipo, msg = "ok", ""
        for filho in tc:
            if filho.tag in ("failure", "error", "skipped"):
                tipo = {"failure": "falha", "error": "erro", "skipped": "pulado"}[filho.tag]
                linhas = (filho.get("message") or (filho.text or "")).strip().splitlines()
                msg = linhas[0] if linhas else ""
                break
        casos.append({"classe": tc.get("classname", ""), "nome": tc.get("name", ""),
                      "arquivo": tc.get("file", ""), "tipo": tipo, "msg": msg})
    return casos


def ler_varios(caminhos):
    """Junta os casos de mais de um relatório (uma suíte em pytest e outra em node, por exemplo)."""
    casos = []
    for c in caminhos:
        casos += ler_junit(c)
    return casos


def modulo(arquivo):
    """api/tests/test_x.py -> api.tests.test_x (como o pytest escreve em classname)."""
    return ".".join(Path(arquivo).with_suffix("").parts)


def caso_do_arquivo(caso, arquivo):
    if caso["arquivo"]:
        return Path(caso["arquivo"]).as_posix() == Path(arquivo).as_posix()
    m = modulo(arquivo)
    return caso["classe"] in (m, Path(arquivo).as_posix()) or caso["classe"].startswith(m + ".")


def id_do_caso(caso):
    return f"{caso['arquivo'] or caso['classe']}::{caso['nome']}"
