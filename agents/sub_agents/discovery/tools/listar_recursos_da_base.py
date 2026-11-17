import os
import re
from collections import Counter
from typing import Any

import requests
from dotenv import load_dotenv
from langchain.tools import tool

from agents.tools.commons.settings import (
    LIMIARES_DETECCAO,
    REGEX_PATTERNS,
    REGEX_REPLACEMENTS,
)

load_dotenv()

_RE_ANO = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")
_RE_SEQUENCIA = re.compile(r"\b(0\d|[1-9]\d?)\b")
_RE_TOKENS = re.compile(r"[_\-\s\.]+")
_RE_SEPARADORES = re.compile(r"[_\-\s]+")
_SEPARADORES_PREFIXO = ("_", "-", ".", " ")
_UNIDADES_TAMANHO = (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024))

# ================= TOOL FUNCTIONS


def _formatar_tamanho(size_bytes: int | None) -> str:
    """Converte bytes para a maior unidade legível (ex.: '1.5 MB')."""
    if not size_bytes:
        return "N/A"
    for unidade, divisor in _UNIDADES_TAMANHO:
        if size_bytes >= divisor:
            return f"{size_bytes / divisor:.1f} {unidade}"
    return f"{size_bytes} B"


def _resumir_recurso(r: dict) -> dict:
    """Campos do recurso expostos ao agente."""
    return {
        "id": r.get("id"),
        "name": r.get("name"),
        "description": r.get("description") or "",
        "format": (r.get("format") or "").upper(),
        "size": _formatar_tamanho(r.get("size")),
        "url": r.get("url"),
        "created": (r.get("created") or "")[:10],
        "last_modified": (r.get("last_modified") or "")[:10],
    }


@tool("listar_recursos_da_base")
def listar_recursos_da_base(
    package_id: str,
    termo_busca: str | None = None,
    limite: int = 20,
    analisar_padroes: bool = True,
    pagina: int = 1,
) -> Any:
    """Lista recursos de uma base com análise de padrões e paginação"""

    try:
        url = os.getenv("URL_CONSULTAR_PROCESSAR_ARQUIVO").format(package_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        if not data.get("success"):
            return {"erro": "Package não encontrado", "sucesso": False}

        package_info = data["result"]
        resources = package_info.get("resources", [])

        if not resources:
            return {
                "package_id": package_id,
                "package_title": package_info.get("title", ""),
                "total_recursos": 0,
                "recursos": [],
                "sucesso": False,
            }

        termos = termo_busca.lower().split() if termo_busca else []
        recursos_filtrados = [
            _resumir_recurso(r)
            for r in resources
            if not termos
            or all(
                t in f"{r.get('name') or ''} {r.get('description') or ''}".lower()
                for t in termos
            )
        ]

        limite = max(1, limite)
        total_filtrados = len(recursos_filtrados)
        total_paginas = max(1, (total_filtrados + limite - 1) // limite)
        pagina = min(max(1, pagina), total_paginas)
        inicio = (pagina - 1) * limite
        recursos_limitados = recursos_filtrados[inicio : inicio + limite]

        padroes_info = None
        if analisar_padroes:
            padroes_info = {}
            if recursos_filtrados:
                nomes = [r.get("name") or "" for r in resources]
                padroes_info = {
                    "prefixos": _detectar_prefixos(nomes),
                    "estruturas": _detectar_estruturas(nomes),
                    "padroes_numericos": _detectar_padroes_numericos(nomes),
                    "palavras_frequentes": _detectar_palavras(nomes),
                }

        notes = package_info.get("notes") or ""
        package_description = notes[:200] + "..." if len(notes) > 200 else notes

        return {
            "package_id": package_id,
            "package_title": package_info.get("title", ""),
            "package_description": package_description,
            "total_recursos_na_base": len(resources),
            "recursos_encontrados": total_filtrados,
            "pagina_atual": pagina,
            "total_paginas": total_paginas,
            "tem_proxima_pagina": pagina < total_paginas,
            "recursos_retornados": len(recursos_limitados),
            "recursos": recursos_limitados,
            "padroes": padroes_info,
            "sucesso": True,
        }

    except requests.exceptions.Timeout:
        return {"erro": "Timeout na requisição", "sucesso": False}
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro de rede: {e}", "sucesso": False}
    except Exception as e:
        return {"erro": f"Erro: {e}", "sucesso": False}


# ================= DETECCAO PADRAO


def _percentual(freq: int, total: int) -> float:
    return round((freq / total) * 100, 1)


def _detectar_prefixos(nomes: list[str]) -> list[dict]:
    """Detecta prefixos comuns"""
    total = len(nomes)
    if total < 2:
        return []

    prefixos = Counter()
    for nome in nomes:
        for sep in _SEPARADORES_PREFIXO:
            partes = nome.split(sep)
            if len(partes) >= 2 and len(partes[0]) > 1:
                prefixos[partes[0].upper()] += 1
                if len(partes) >= 3 and len(partes[1]) > 1:
                    prefixos[f"{partes[0]}{sep}{partes[1]}".upper()] += 1

    nomes_upper = [n.upper() for n in nomes]
    limiar = total * LIMIARES_DETECCAO["prefixo_separador"]
    resultados = []

    # most_common já vem ordenado: os que passam do limiar formam um prefixo da lista
    for prefixo, freq in prefixos.most_common(3):
        if freq > limiar:
            indice = next((i for i, n in enumerate(nomes_upper) if prefixo in n), None)
            resultados.append(
                {
                    "prefixo": prefixo,
                    "frequencia": freq,
                    "percentual": _percentual(freq, total),
                    "exemplo": nomes[indice] if indice is not None else "",
                }
            )

    return resultados


def _detectar_estruturas(nomes: list[str]) -> list[dict]:
    """Detecta padrões de estrutura de nomes"""
    estruturas = Counter()
    exemplo_do_template = {}

    for nome in nomes:
        template = nome
        for chave, padrao in REGEX_PATTERNS.items():
            template = re.sub(padrao, REGEX_REPLACEMENTS[chave], template)
        template = _RE_SEPARADORES.sub("_", template).upper()
        exemplo_do_template.setdefault(
            template, nome
        )  # primeiro nome com esse template
        estruturas[template] += 1

    return [
        {
            "template": estrutura,
            "frequencia": freq,
            "percentual": _percentual(freq, len(nomes)),
            "exemplo": exemplo_do_template[estrutura],
        }
        for estrutura, freq in estruturas.most_common(3)
        if freq > 1
    ]


def _detectar_padroes_numericos(nomes: list[str]) -> dict:
    """Detecta anos, datas e sequências"""
    anos_detectados = set()
    sequencias = set()

    for nome in nomes:
        anos_detectados.update(_RE_ANO.findall(nome))
        sequencias.update(int(s) for s in _RE_SEQUENCIA.findall(nome))

    resultado = {}

    if anos_detectados:
        anos_sorted = sorted(anos_detectados)
        resultado["anos"] = {
            "lista": anos_sorted,
            "range": f"{anos_sorted[0]}-{anos_sorted[-1]}",
        }

    if len(sequencias) > LIMIARES_DETECCAO["min_sequencias"]:
        menor, maior = min(sequencias), max(sequencias)
        resultado["sequencias"] = {
            "range": f"{menor:02d}-{maior:02d}",
            "pode_ser_mes": maior <= 12,
            "pode_ser_dia": maior <= 31,
        }

    return resultado


def _detectar_palavras(nomes: list[str]) -> list[dict]:
    """Detecta palavras frequentes"""
    palavras = Counter()

    for nome in nomes:
        tokens = _RE_TOKENS.split(nome.split(".")[0].upper())  # descarta a extensão
        palavras.update(t for t in tokens if len(t) > 2 and not t.isdigit())

    nomes_upper = [n.upper() for n in nomes]
    resultados = []
    for palavra, freq in palavras.most_common(10):
        if freq > LIMIARES_DETECCAO["min_frequencia"]:
            exemplos = [n for n, up in zip(nomes, nomes_upper) if palavra in up][:2]
            resultados.append(
                {
                    "palavra": palavra,
                    "frequencia": freq,
                    "percentual": _percentual(freq, len(nomes)),
                    "exemplos": exemplos,
                }
            )

    return resultados
