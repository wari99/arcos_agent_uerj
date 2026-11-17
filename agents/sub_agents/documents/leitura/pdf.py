"""Leitura de PDF com pdfplumber: texto limpo, tabelas em Markdown, detecção de páginas sem texto e renderização."""
import io
import re
from dataclasses import dataclass, field

import pdfplumber

from agents.sub_agents.documents.leitura.fonte import ErroDocumento
from agents.sub_agents.documents.leitura.limpeza import detectar_repetidos, limpar_texto
from agents.tools.commons.core import get_logger

logger = get_logger("documents")

AMOSTRA_REPETIDOS = 12  # páginas usadas para descobrir cabeçalhos e rodapés
LIMITE_MAPEAR_PAGINAS = 100  # páginas analisadas no mapeamento
LIMITE_MAPEAR_TABELAS = 40  # procurar tabelas custa caro: só nas primeiras páginas
MIN_CHARS_COM_TEXTO = 25
MAX_LINHAS_TABELA = 80
MIN_OBJETOS_GRAFICO = 20
MAX_CHARS_CELULA = (
    300  # célula maior que isso: a detecção juntou a página inteira numa célula
)
MIN_CELULAS_PREENCHIDAS = 4
PAGINAS_PADRAO = 5


@dataclass
class PaginaExtraida:
    numero: int
    texto: str
    tabelas: list[str] = field(default_factory=list)
    n_chars: int = 0
    n_imagens: int = 0
    possivel_grafico: bool = False
    tabelas_rejeitadas: int = 0  # detectadas, mas sem estrutura aproveitável

    @property
    def sem_texto(self) -> bool:
        return self.n_chars < MIN_CHARS_COM_TEXTO


# estado por arquivo, para não reprocessar a cada chamada de ferramenta
_REPETIDOS: dict[str, set] = {}
_PAGINAS: dict[tuple, PaginaExtraida] = {}
_TEXTO_BUSCA: dict[str, list[str]] = {}


def _abrir(caminho: str):
    try:
        return pdfplumber.open(caminho)
    except Exception as e:
        if "password" in type(e).__name__.lower() or "password" in str(e).lower():
            raise ErroDocumento("O PDF é protegido por senha.")
        raise ErroDocumento(f"Não consegui abrir o PDF: {e}")


def total_paginas(caminho: str) -> int:
    with _abrir(caminho) as pdf:
        return len(pdf.pages)


def interpretar_intervalo(expressao: str | None, total: int) -> list[int]:
    """'1-3,7' -> [1,2,3,7]. Sem expressão: as primeiras páginas."""
    if not expressao or not str(expressao).strip():
        return list(range(1, min(total, PAGINAS_PADRAO) + 1))

    paginas: list[int] = []
    for parte in str(expressao).replace(" ", "").split(","):
        if not parte:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", parte)
        if not m:
            raise ErroDocumento(
                f"Intervalo de páginas inválido: '{expressao}'. Use, por exemplo, '1-3,7'."
            )
        inicio = int(m.group(1))
        fim = int(m.group(2) or inicio)
        if inicio < 1 or fim < inicio or fim > total:
            raise ErroDocumento(
                f"Páginas fora do documento (ele tem {total}): '{parte}'."
            )
        paginas.extend(range(inicio, fim + 1))

    return sorted(set(paginas))


def _repetidos(pdf, caminho: str) -> set:
    if caminho not in _REPETIDOS:
        total = len(pdf.pages)
        passo = max(1, total // AMOSTRA_REPETIDOS)
        indices = list(range(0, total, passo))[:AMOSTRA_REPETIDOS]
        amostra = [pdf.pages[i].extract_text() or "" for i in indices]
        _REPETIDOS[caminho] = detectar_repetidos(amostra)
    return _REPETIDOS[caminho]


def _para_markdown(tabela: list[list[str | None]], numero: int) -> str | None:
    linhas = [
        [(c or "").replace("\n", " ").replace("|", "/").strip() for c in linha]
        for linha in tabela
    ]
    linhas = [l for l in linhas if any(l)]
    if len(linhas) < 2 or max(len(l) for l in linhas) < 2:
        return None  # ruído: uma "tabela" de uma linha ou coluna só
    celulas = [c for l in linhas for c in l if c]
    if (
        len(celulas) < MIN_CELULAS_PREENCHIDAS
        or max(len(c) for c in celulas) > MAX_CHARS_CELULA
    ):
        return None  # tabela degenerada: melhor o texto simples do que células com a página inteira

    largura = max(len(l) for l in linhas)
    linhas = [l + [""] * (largura - len(l)) for l in linhas]
    colunas_vazias = [i for i in range(largura) if not any(l[i] for l in linhas)]
    linhas = [[c for i, c in enumerate(l) if i not in colunas_vazias] for l in linhas]
    largura = len(linhas[0])

    omitidas = max(0, len(linhas) - MAX_LINHAS_TABELA)
    linhas = linhas[:MAX_LINHAS_TABELA]
    md = ["| " + " | ".join(linhas[0]) + " |", "|" + "---|" * largura]
    md += ["| " + " | ".join(l) + " |" for l in linhas[1:]]
    if omitidas:
        md.append(f"(… {omitidas} linhas omitidas)")
    return "\n".join(md)


def _parece_grafico(pagina, tem_tabela: bool) -> bool:
    """Muitos traços/formas desenhados numa página SEM tabela.
    Curvas e retângulos sozinhos não servem: bordas e cantos arredondados de tabelas também os produzem."""
    if tem_tabela:
        return False
    return (
        len(pagina.curves) + len(pagina.rects) + len(pagina.lines)
        >= MIN_OBJETOS_GRAFICO
    )


def _fora_das_tabelas(pagina, caixas):
    def manter(obj):
        if obj.get("object_type") != "char":
            return True
        x = (obj["x0"] + obj["x1"]) / 2
        y = (obj["top"] + obj["bottom"]) / 2
        return not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in caixas)

    return pagina.filter(manter)


def _extrair(pdf, caminho: str, numero: int) -> PaginaExtraida:
    pagina = pdf.pages[numero - 1]
    repetidos = _repetidos(pdf, caminho)

    tabelas_md: list[str] = []
    caixas = []
    rejeitadas = 0
    try:
        for t in pagina.find_tables():
            md = _para_markdown(t.extract(), numero)
            if md:
                tabelas_md.append(md)
                caixas.append(t.bbox)
            else:
                rejeitadas += 1
    except Exception as e:
        logger.warning(
            "Falha ao extrair tabelas do PDF: %s", e
        )  # tabela é um extra: falhar aqui não pode derrubar a leitura do texto

    origem = _fora_das_tabelas(pagina, caixas) if caixas else pagina
    texto = limpar_texto(origem.extract_text() or "", repetidos)

    return PaginaExtraida(
        numero=numero,
        texto=texto,
        tabelas=tabelas_md,
        n_chars=len(pagina.chars),
        n_imagens=len(pagina.images),
        possivel_grafico=_parece_grafico(pagina, bool(tabelas_md)),
        tabelas_rejeitadas=rejeitadas,
    )


def extrair_paginas(caminho: str, numeros: list[int]) -> list[PaginaExtraida]:
    faltam = [n for n in numeros if (caminho, n) not in _PAGINAS]
    if faltam:
        with _abrir(caminho) as pdf:
            for n in faltam:
                try:
                    _PAGINAS[(caminho, n)] = _extrair(pdf, caminho, n)
                except ErroDocumento:
                    raise
                except Exception as e:
                    raise ErroDocumento(f"Falha ao ler a página {n}: {e}")
    return [_PAGINAS[(caminho, n)] for n in numeros]


def mapear(caminho: str) -> dict:
    with _abrir(caminho) as pdf:
        total = len(pdf.pages)
        analisar = min(total, LIMITE_MAPEAR_PAGINAS)
        sem_texto, com_imagens, com_tabelas, possivel_grafico = [], [], [], []

        for n in range(1, analisar + 1):
            pagina = pdf.pages[n - 1]
            chars = len(pagina.chars)
            if chars < MIN_CHARS_COM_TEXTO:
                sem_texto.append(n)
            if pagina.images:
                com_imagens.append(n)
            if (
                n <= LIMITE_MAPEAR_TABELAS
            ):  # sem saber se há tabela a heurística de gráfico n vale
                tem_tabela = False
                try:
                    tem_tabela = any(
                        _para_markdown(t.extract(), n) for t in pagina.find_tables()
                    )
                except Exception as e:
                    logger.warning(
                        "Falha ao identificar tabelas na página %s: %s", n, e
                    )
                if tem_tabela:
                    com_tabelas.append(n)
                if _parece_grafico(pagina, tem_tabela):
                    possivel_grafico.append(n)

        sumario = []
        try:
            for nivel, titulo, *_ in pdf.doc.get_outlines():
                sumario.append(f"{'  ' * (nivel - 1)}{titulo}")
                if len(sumario) >= 40:
                    break
        except Exception as e:
            logger.debug("PDF sem marcadores ou falha ao identificá-los: %s", e)

        inicio = ""
        if total:
            inicio = limpar_texto(pdf.pages[0].extract_text() or "", set())[:500]

        return {
            "total_paginas": total,
            "paginas_analisadas": analisar,
            "tabelas_analisadas_ate": min(total, LIMITE_MAPEAR_TABELAS),
            "sem_texto": sem_texto,
            "com_imagens": com_imagens,
            "com_tabelas": com_tabelas,
            "possivel_grafico": possivel_grafico,
            "escaneado": analisar > 0 and len(sem_texto) >= 0.6 * analisar,
            "sumario": sumario,
            "inicio": inicio,
            "metadados": {
                k: str(v)
                for k, v in (pdf.metadata or {}).items()
                if k in ("Title", "Author", "CreationDate")
            },
        }


def texto_para_busca(caminho: str) -> list[str]:
    """Texto limpo de cada página (sem a separação de tabelas, que é cara), para buscar termos."""
    if caminho not in _TEXTO_BUSCA:
        with _abrir(caminho) as pdf:
            repetidos = _repetidos(pdf, caminho)
            _TEXTO_BUSCA[caminho] = [
                limpar_texto(p.extract_text() or "", repetidos) for p in pdf.pages
            ]
    return _TEXTO_BUSCA[caminho]


def renderizar_png(caminho: str, numero: int, resolucao: int = 130) -> bytes:
    with _abrir(caminho) as pdf:
        if not 1 <= numero <= len(pdf.pages):
            raise ErroDocumento(
                f"Página {numero} fora do documento (ele tem {len(pdf.pages)})."
            )
        imagem = pdf.pages[numero - 1].to_image(resolution=resolucao).original
        buffer = io.BytesIO()
        imagem.save(buffer, format="PNG")
        return buffer.getvalue()
