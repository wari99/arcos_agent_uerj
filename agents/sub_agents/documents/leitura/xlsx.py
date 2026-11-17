"""Leitura de XLSX como documento (não como tabela de dados): todas as abas, título, notas, células mescladas."""
import datetime as dt
from typing import Any

import openpyxl

from agents.sub_agents.documents.leitura.fonte import ErroDocumento, normalizar

LIMITE_LEITURA_COMPLETA_MB = (
    15  # acima disso usa modo "read_only" (sem mesclagens, mas com pouca memória)
)
LINHAS_VARREDURA_CABECALHO = 20
MAX_COLUNAS = 20
MAX_CELULAS_BUSCA = 300_000


def _abrir(caminho: str, tamanho_mb: float):
    try:
        return openpyxl.load_workbook(
            caminho,
            data_only=True,  # valor calculado, não a fórmula
            read_only=tamanho_mb > LIMITE_LEITURA_COMPLETA_MB,
        )
    except Exception as e:
        raise ErroDocumento(f"Não consegui abrir a planilha: {e}")


def _fmt(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return str(int(valor)) if valor.is_integer() else f"{valor:.6g}"
    if isinstance(valor, dt.datetime):
        return (
            valor.date().isoformat()
            if valor.time() == dt.time(0)
            else valor.isoformat(sep=" ")
        )
    if isinstance(valor, dt.date):
        return valor.isoformat()
    return str(valor).replace("\n", " ").replace("|", "/").strip()


def _valores_mesclados(ws) -> dict[tuple[int, int], Any]:
    """Células mescladas guardam o valor só no canto superior esquerdo; copia para o resto da área."""
    copias: dict[tuple[int, int], Any] = {}
    for intervalo in (
        getattr(ws, "merged_cells", None).ranges
        if getattr(ws, "merged_cells", None)
        else []
    ):
        valor = ws.cell(intervalo.min_row, intervalo.min_col).value
        if valor is None:
            continue
        for linha in range(intervalo.min_row, intervalo.max_row + 1):
            for coluna in range(intervalo.min_col, intervalo.max_col + 1):
                if (linha, coluna) != (intervalo.min_row, intervalo.min_col):
                    copias[(linha, coluna)] = valor
    return copias


def _linhas(ws, limite: int | None = None) -> list[tuple[int, list[Any], list[Any]]]:
    """(número da linha, valores brutos, valores com mesclagens preenchidas) das linhas com algum conteúdo.
    O cabeçalho é detectado nos valores brutos: um título mesclado preenchido em todas as colunas
    pareceria um cabeçalho. O preenchimento serve ao corpo da tabela (células mescladas na vertical)."""
    mesclados = _valores_mesclados(ws)
    saida = []
    for linha in ws.iter_rows():
        celulas = [c for c in linha if hasattr(c, "row")]
        brutos = [c.value for c in celulas]
        if any(v is not None and str(v).strip() for v in brutos):
            preenchidos = [
                c.value if c.value is not None else mesclados.get((c.row, c.column))
                for c in celulas
            ]
            saida.append((celulas[0].row, brutos, preenchidos))
            if limite and len(saida) >= limite:
                break
    return saida


def _tem_conteudo(ws) -> bool:
    return any(
        any(v is not None and str(v).strip() for v in linha)
        for linha in ws.iter_rows(max_row=50, values_only=True)
    )


def _cabecalho(linhas: list[tuple[int, list[Any], list[Any]]]) -> int:
    """Índice (em 'linhas') da linha de cabeçalho: a primeira larga e majoritariamente textual."""
    janela = linhas[:LINHAS_VARREDURA_CABECALHO]
    preenchidas = [
        sum(1 for v in l if v is not None and str(v).strip()) for _, l, _ in janela
    ]
    if not preenchidas:
        return 0
    largura = max(preenchidas)
    for i, (_, valores, _) in enumerate(janela):
        cheios = [v for v in valores if v is not None and str(v).strip()]
        textuais = [v for v in cheios if isinstance(v, str)]
        if len(cheios) >= max(2, 0.6 * largura) and len(textuais) >= 0.6 * len(cheios):
            return i
    return 0


def mapear(caminho: str, tamanho_mb: float) -> list[dict]:
    wb = _abrir(caminho, tamanho_mb)
    abas = []
    try:
        for ws in wb.worksheets:
            info = {
                "aba": ws.title,
                "dimensoes": ws.dimensions if hasattr(ws, "dimensions") else "?",
                "visivel": getattr(ws, "sheet_state", "visible") == "visible",
                "mesclagens": len(ws.merged_cells.ranges)
                if getattr(ws, "merged_cells", None)
                else 0,
                "graficos": len(getattr(ws, "_charts", []) or []),
                "imagens": len(getattr(ws, "_images", []) or []),
            }
            abas.append(info)
    finally:
        wb.close()
    return abas


def ler_aba(caminho: str, tamanho_mb: float, aba: str | None, max_linhas: int) -> dict:
    wb = _abrir(caminho, tamanho_mb)
    try:
        nomes = [ws.title for ws in wb.worksheets]
        if not nomes:
            raise ErroDocumento("A planilha não tem abas.")

        if aba:
            alvo = next(
                (n for n in nomes if normalizar(n) == normalizar(aba)), None
            ) or next((n for n in nomes if normalizar(aba) in normalizar(n)), None)
            if not alvo:
                raise ErroDocumento(f"Aba '{aba}' não existe. Abas: {', '.join(nomes)}")
        else:  # primeira aba que tenha conteúdo
            alvo = next((n for n in nomes if _tem_conteudo(wb[n])), nomes[0])

        ws = wb[alvo]
        linhas = _linhas(ws)
        if not linhas:
            return {"aba": alvo, "abas": nomes, "vazia": True}

        idx = _cabecalho(linhas)
        introducao = [
            " | ".join(_fmt(v) for v in bruto if v is not None and str(v).strip())
            for _, bruto, _ in linhas[:idx]
        ]
        cabecalho = linhas[idx][2][:MAX_COLUNAS]
        corpo = linhas[idx + 1 :]

        largura = len(cabecalho)
        nomes_colunas = [_fmt(c) or f"col{i + 1}" for i, c in enumerate(cabecalho)]
        mostradas = corpo[:max_linhas]
        tabela = [nomes_colunas] + [
            [_fmt(v) for v in (l + [None] * largura)[:largura]] for _, _, l in mostradas
        ]

        return {
            "aba": alvo,
            "abas": nomes,
            "introducao": introducao[:10],
            "linha_cabecalho": linhas[idx][0],
            "tabela": tabela,
            "linhas_total": len(corpo),
            "linhas_mostradas": len(mostradas),
            "colunas_total": len(linhas[idx][2]),
            "colunas_mostradas": largura,
            "vazia": False,
        }
    finally:
        wb.close()


def tabela_markdown(tabela: list[list[str]]) -> str:
    if not tabela:
        return ""
    largura = len(tabela[0])
    linhas = ["| " + " | ".join(tabela[0]) + " |", "|" + "---|" * largura]
    linhas += ["| " + " | ".join(l) + " |" for l in tabela[1:]]
    return "\n".join(linhas)


def buscar(caminho: str, tamanho_mb: float, termo: str, maximo: int) -> list[dict]:
    alvo = normalizar(termo)
    wb = _abrir(caminho, tamanho_mb)
    achados: list[dict] = []
    vistos = 0
    try:
        for ws in wb.worksheets:
            for linha in ws.iter_rows():
                celulas = [c for c in linha if hasattr(c, "row")]
                for c in celulas:
                    vistos += 1
                    if c.value is not None and alvo in normalizar(str(c.value)):
                        contexto = " | ".join(
                            _fmt(x.value) for x in celulas if x.value is not None
                        )
                        achados.append(
                            {
                                "aba": ws.title,
                                "celula": c.coordinate,
                                "linha": contexto[:200],
                            }
                        )
                        if len(achados) >= maximo:
                            return achados
                    if vistos >= MAX_CELULAS_BUSCA:
                        return achados
    finally:
        wb.close()
    return achados
