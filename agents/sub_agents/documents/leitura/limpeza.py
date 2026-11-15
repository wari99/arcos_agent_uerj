"""Limpeza de texto extraído de PDF: linhas em branco, números de página, cabeçalhos/rodapés repetidos."""
import re
from collections import Counter
from typing import List, Set

_PAGINA_EXPLICITA = re.compile(
    r"^\s*[-–—]?\s*(?:p[áa]g(?:ina)?\.?|page)\s*\d+(?:\s*(?:de|/|of)\s*\d+)?\s*[-–—]?\s*$", re.I
)
_N_DE_M = re.compile(r"^\s*\d{1,4}\s*(?:/|de|of)\s*\d{1,4}\s*$", re.I)
_NUMERO_SOZINHO = re.compile(r"^\s*[-–—]?\s*\d{1,3}\s*[-–—]?\s*$")
_PONTILHADO = re.compile(r"(?:\.\s?){4,}")  # sumários: "Capítulo 1 ........ 5"
_HIFEN_FINAL = re.compile(r"[A-Za-zÀ-ÿ]-$")

MIN_PAGINAS_PARA_REPETIDOS = 4
LINHAS_DE_BORDA = 2  # quantas linhas no topo/rodapé são candidatas a cabeçalho/rodapé


def chave_repeticao(linha: str) -> str:
    """Normaliza para comparar cabeçalhos que só diferem pelo número da página."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", linha.strip().lower()))


def _linhas_nao_vazias(texto: str) -> List[str]:
    return [re.sub(r"[ \t]+", " ", l).strip() for l in (texto or "").splitlines() if l.strip()]


def detectar_repetidos(textos_paginas: List[str]) -> Set[str]:
    """Linhas do topo/rodapé que aparecem na maioria das páginas amostradas."""
    if len(textos_paginas) < MIN_PAGINAS_PARA_REPETIDOS:
        return set()

    contagem: Counter = Counter()
    for texto in textos_paginas:
        linhas = _linhas_nao_vazias(texto)
        bordas = set(linhas[:LINHAS_DE_BORDA]) | set(linhas[-LINHAS_DE_BORDA:])
        contagem.update({chave_repeticao(l) for l in bordas})

    minimo = max(3, int(0.4 * len(textos_paginas)))
    return {chave for chave, n in contagem.items() if n >= minimo and chave}


def limpar_texto(texto: str, repetidos: Set[str]) -> str:
    """Remove linhas em branco, marcas de página e cabeçalhos/rodapés repetidos; junta palavras hifenizadas."""
    linhas = _linhas_nao_vazias(texto)
    resultado: List[str] = []

    for i, linha in enumerate(linhas):
        na_borda = i < LINHAS_DE_BORDA or i >= len(linhas) - LINHAS_DE_BORDA
        if _PAGINA_EXPLICITA.match(linha) or _N_DE_M.match(linha):
            continue
        if (i == 0 or i == len(linhas) - 1) and _NUMERO_SOZINHO.match(linha):
            continue
        if na_borda and chave_repeticao(linha) in repetidos:
            continue
        resultado.append(_PONTILHADO.sub(" … ", linha))

    # palavra quebrada no fim da linha ("trans-" / "porte") volta a ser uma palavra só
    juntas: List[str] = []
    for linha in resultado:
        if juntas and _HIFEN_FINAL.search(juntas[-1]) and linha[:1].islower():
            juntas[-1] = juntas[-1][:-1] + linha
        else:
            juntas.append(linha)

    return "\n".join(juntas)
