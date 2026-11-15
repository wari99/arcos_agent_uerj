"""
Tool `analisar_dados_arquivo`: executa uma operação de análise nos arquivos de uma base.

Como funciona, em ordem:
1. Confere os parâmetros obrigatórios da operação pedida.
2. Obtém os arquivos (do cache ou baixando).
3. Roda a operação em CADA arquivo e guarda um resultado por arquivo.
4. Monta o `_resumo_analise`: contagem de sucessos e erros, cabeçalho real dos arquivos,
   total geral (quando há vários arquivos) e avisos.

As operações em si ficam em agents/tools/commons/_operacoes_*.py.
Aqui só ligamos cada nome de operação à função que a executa (veja _OPERACOES).
"""

import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Optional, get_args

from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from agents.sub_agents.analysis.tools.gerenciar_cache_sessao import obter_arquivos_para_analise
from agents.tools.commons._operacoes_basicas import (
    executar_contar_linhas,
    executar_estatistica,
    executar_mostrar_colunas,
    executar_preview,
    executar_valores_unicos,
)
from agents.tools.commons._operacoes_concessionarias import executar_leitura_tarifa
from agents.tools.commons._operacoes_filtros import (
    executar_agrupar_e_somar,
    executar_agrupar_valores_unicos,
    executar_contar_por_valor,
    executar_contar_unicos,
)
from agents.tools.commons._operacoes_turnos import (
    executar_comparar_por_turno,
    executar_contar_por_turno,
    executar_filtrar_por_turno,
)
from agents.tools.commons.core import logger
from agents.tools.commons.settings import FAIXAS_HORARIAS
from agents.tools.commons.utils import obter_pasta_temporaria

Operacao = Literal[
    "contar_linhas", "mostrar_colunas", "preview",
    "media", "soma", "max", "min",
    "valores_unicos", "agrupar_valores_unicos",
    "contar_por_valor", "contar_unicos", "agrupar_e_somar",
    "filtrar_por_turno", "contar_por_turno", "comparar_por_turno",
    "leitura_tarifa",
]

# Parâmetros obrigatórios por operação (a checagem roda antes de carregar o arquivo)
_EXIGIDOS = {
    "valores_unicos": ("coluna",),
    "agrupar_valores_unicos": ("coluna",),
    "contar_por_valor": ("coluna", "valor"),
    "contar_unicos": ("coluna_alvo",),
    "agrupar_e_somar": ("coluna", "valor", "coluna_soma"),
}

_EXEMPLOS = {
    "valores_unicos": {"operation": "valores_unicos", "coluna": "Linha"},
    "agrupar_valores_unicos": {"operation": "agrupar_valores_unicos", "coluna": "Linha"},
    "contar_por_valor": {"operation": "contar_por_valor", "coluna": "Modal Operadora", "valor": "ÔNIBUS"},
    "contar_unicos": {"operation": "contar_unicos", "coluna_alvo": "Nº Carro", "coluna": "Sindicato", "valor": "SINTERJ"},
    "agrupar_e_somar": {"operation": "agrupar_e_somar", "coluna": "Modal Operadora", "valor": "ÔNIBUS", "coluna_soma": "Qtd. Transações"},
}

# Operações cujo filtro (coluna + valor) é opcional, mas os dois precisam vir juntos
_OPERACOES_COM_FILTRO_OPCIONAL = ("contar_unicos", "filtrar_por_turno", "contar_por_turno", "comparar_por_turno")

# Coluna de data usada nas operações de turno quando o modelo não informa outra
COLUNA_DATA_PADRAO = "Data da Transação"


class AnalisarArgs(BaseModel):
    """Parâmetros de analisar_dados_arquivo. Cada campo diz em quais operações é usado."""

    package_id: str = Field(description="id da base (ex: 'setram_sbe')")
    operation: Operacao = Field("contar_linhas", description="operação a executar")
    file_filter: str = Field("", description="parte do nome do arquivo (ex: '2025_12_20') ou nome completo")
    coluna: Optional[str] = Field(
        None,
        description="coluna sobre a qual a operação age. Obrigatória em valores_unicos, agrupar_valores_unicos, "
                    "contar_por_valor e agrupar_e_somar. Opcional (filtro) em contar_unicos, filtrar_por_turno, "
                    "contar_por_turno e comparar_por_turno, onde deve vir junto com 'valor'",
    )
    valor: Optional[str] = Field(
        None,
        description="valor procurado em 'coluna' (busca parcial, sem diferenciar maiúsculas; ex: 'Idoso'). "
                    "Obrigatório em contar_por_valor e agrupar_e_somar",
    )
    coluna_soma: Optional[str] = Field(
        None, description="coluna numérica a somar (ex: 'Qtd. Transações'). Obrigatória em agrupar_e_somar"
    )
    coluna_alvo: Optional[str] = Field(
        None,
        description="coluna cujos valores DISTINTOS serão contados (ex: 'Nº Carro'). Obrigatória em contar_unicos; "
                    "para contar só dentro de um grupo, informe também 'coluna' e 'valor' (o filtro)",
    )
    coluna_data: Optional[str] = Field(
        None,
        description="coluna com data. Nas operações de turno: data e hora da transação (padrão: 'Data da Transação'). "
                    "Em leitura_tarifa: coluna com o início da vigência da tarifa",
    )
    turno: Optional[str] = Field(
        None, description="só em filtrar_por_turno: 0=Madrugada, 1=Manhã, 2=Tarde, 3=Noite ou 'todos' (padrão)"
    )
    limite: Optional[int] = Field(
        None,
        description="itens por página. Só em valores_unicos (padrão 15) e agrupar_valores_unicos "
                    "(padrão 10 = top 10; máximo 100 por chamada)",
    )
    offset: int = Field(
        0,
        description="quantos itens pular. Só em valores_unicos e agrupar_valores_unicos "
                    "(ex.: offset=10 em agrupar_valores_unicos traz do 11º ao 20º lugar)",
    )
    consulta_tipo: str = Field(
        "atual", description="só em leitura_tarifa: atual, ano, ultima_mudanca, historico ou buscar_por_valor"
    )
    ano: Optional[int] = Field(None, description="só em leitura_tarifa: ano da consulta")
    coluna_tarifa: Optional[str] = Field(
        None, description="só em leitura_tarifa: coluna com o valor da tarifa (ex: 'Tarifa Autorizada (R$)')"
    )
    coluna_descricao: Optional[str] = Field(
        None,
        description="só em leitura_tarifa: coluna que identifica ou descreve cada tarifa "
                    "(ex: 'Linha - Trajeto', 'Descrição', 'Deliberação'). Opcional",
    )
    linha_cabecalho: Optional[int] = Field(
        None,
        description="só em leitura_tarifa: posição (0 = primeira linha mostrada no 'preview') da linha que contém "
                    "os nomes reais das colunas, quando a planilha tem títulos antes do cabeçalho. Opcional",
    )

    @field_validator(
        "coluna", "valor", "coluna_soma", "coluna_alvo", "coluna_data", "turno", "coluna_tarifa", "coluna_descricao",
        mode="before",
    )
    @classmethod
    def _para_texto(cls, v):
        # o modelo às vezes manda números (turno=1, valor=7001); aceita e converte
        return str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


@dataclass
class Parametros:
    """Os parâmetros da chamada, reunidos para passar às funções de cada operação."""

    operacao: str
    coluna: Optional[str] = None
    valor: Optional[str] = None
    coluna_soma: Optional[str] = None
    coluna_alvo: Optional[str] = None
    coluna_data: Optional[str] = None
    turno: str = "todos"
    limite: Optional[int] = None
    offset: int = 0
    consulta_tipo: str = "atual"
    ano: Optional[int] = None
    coluna_tarifa: Optional[str] = None
    coluna_descricao: Optional[str] = None
    linha_cabecalho: Optional[int] = None


# ============================================================
# AS OPERAÇÕES: uma função pequena por operação
# Cada uma recebe o arquivo (dict com df, path, nome, memoria_mb, memo) e os parâmetros,
# e devolve o resultado daquele arquivo.
# ============================================================

def _op_contar_linhas(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_contar_linhas(arquivo["df"], arquivo["path"], memoria_mb=arquivo.get("memoria_mb"))


def _op_mostrar_colunas(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_mostrar_colunas(arquivo["df"], arquivo["path"])


def _op_preview(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_preview(arquivo["df"], arquivo["path"])


def _op_estatistica(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_estatistica(arquivo["df"], p.operacao, arquivo["path"])


def _op_valores_unicos(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    if not p.coluna:
        logger.error("Parâmetro 'coluna' não fornecido")
        return {"erro": "Parâmetro 'coluna' é obrigatório", "sucesso": False}

    limite = 15 if p.limite is None else p.limite
    resultado = executar_valores_unicos(
        df=arquivo["df"], coluna=p.coluna, path=arquivo["path"], limite=limite, offset=p.offset
    )

    if resultado.get("sucesso"):
        logger.info(
            f"Página {resultado['pagina_atual']}/{resultado['total_paginas']} "
            f"({resultado['quantidade_retornada']}/{resultado['quantidade_total']})"
        )
    else:
        logger.error(f"{resultado.get('erro')}")
    return resultado


def _op_contar_por_valor(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_contar_por_valor(df=arquivo["df"], coluna=p.coluna, valor=p.valor, path=arquivo["path"])


def _op_contar_unicos(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_contar_unicos(
        df=arquivo["df"], coluna_alvo=p.coluna_alvo, path=arquivo["path"], coluna=p.coluna, valor=p.valor
    )


def _op_agrupar_e_somar(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_agrupar_e_somar(
        df=arquivo["df"], coluna=p.coluna, valor=p.valor, coluna_soma=p.coluna_soma, path=arquivo["path"]
    )


def _op_agrupar_valores_unicos(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_agrupar_valores_unicos(
        df=arquivo["df"], coluna=p.coluna, path=arquivo["path"], limite=p.limite, offset=p.offset
    )


def _op_filtrar_por_turno(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_filtrar_por_turno(
        df=arquivo["df"], turno=p.turno, coluna_data=p.coluna_data or COLUNA_DATA_PADRAO,
        path=arquivo["path"], coluna=p.coluna, valor=p.valor, memo=arquivo.get("memo"),
    )


def _op_contar_por_turno(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_contar_por_turno(
        df=arquivo["df"], coluna_data=p.coluna_data or COLUNA_DATA_PADRAO,
        path=arquivo["path"], coluna=p.coluna, valor=p.valor, memo=arquivo.get("memo"),
    )


def _op_comparar_por_turno(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    return executar_comparar_por_turno(
        df=arquivo["df"], coluna_data=p.coluna_data or COLUNA_DATA_PADRAO,
        path=arquivo["path"], coluna=p.coluna, valor=p.valor, memo=arquivo.get("memo"),
    )


def _op_leitura_tarifa(arquivo: Dict[str, Any], p: Parametros) -> Dict[str, Any]:
    logger.info(f"LEITURA_TARIFA | consulta: {p.consulta_tipo} | ano: {p.ano}")
    return executar_leitura_tarifa(
        df=arquivo["df"], consulta_tipo=p.consulta_tipo, ano=p.ano, path=arquivo["path"],
        coluna_tarifa=p.coluna_tarifa, coluna_data=p.coluna_data,
        coluna_descricao=p.coluna_descricao, linha_cabecalho=p.linha_cabecalho,
    )


# Liga o nome de cada operação à função que a executa
_OPERACOES: Dict[str, Callable[[Dict[str, Any], Parametros], Dict[str, Any]]] = {
    "contar_linhas": _op_contar_linhas,
    "mostrar_colunas": _op_mostrar_colunas,
    "preview": _op_preview,
    "media": _op_estatistica,
    "soma": _op_estatistica,
    "max": _op_estatistica,
    "min": _op_estatistica,
    "valores_unicos": _op_valores_unicos,
    "agrupar_valores_unicos": _op_agrupar_valores_unicos,
    "contar_por_valor": _op_contar_por_valor,
    "contar_unicos": _op_contar_unicos,
    "agrupar_e_somar": _op_agrupar_e_somar,
    "filtrar_por_turno": _op_filtrar_por_turno,
    "contar_por_turno": _op_contar_por_turno,
    "comparar_por_turno": _op_comparar_por_turno,
    "leitura_tarifa": _op_leitura_tarifa,
}


# ============================================================
# FUNÇÕES DE APOIO
# ============================================================

def _esquemas(arquivos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Cabeçalho real dos arquivos analisados.
    Se todos têm as mesmas colunas, devolve {"colunas": [...]}.
    Se divergirem, devolve um item por esquema, dizendo quais arquivos pertencem a cada um.
    """
    arquivos_por_esquema: Dict[tuple, List[str]] = {}
    for arquivo in arquivos:
        colunas = tuple(str(coluna) for coluna in arquivo["df"].columns)
        arquivos_por_esquema.setdefault(colunas, []).append(arquivo["nome"])

    if len(arquivos_por_esquema) == 1:
        return {"colunas": list(next(iter(arquivos_por_esquema)))}

    esquemas = []
    for colunas, nomes in arquivos_por_esquema.items():
        esquemas.append({"arquivos": nomes, "colunas": list(colunas)})
    return {"colunas_por_esquema": esquemas}


def _remover_colunas_repetidas(resultados: Dict[str, Any], arquivos: List[Dict[str, Any]]) -> None:
    """
    A lista de colunas já vai no _resumo_analise. Tira a cópia que cada resultado carregaria
    (nomes_colunas, colunas_disponiveis) para não repetir os mesmos nomes várias vezes ao modelo.
    """
    for arquivo in arquivos:
        resultado = resultados.get(arquivo["nome"])
        if not isinstance(resultado, dict):
            continue
        colunas_do_arquivo = list(arquivo["df"].columns)
        for chave in ("nomes_colunas", "colunas_disponiveis"):
            if resultado.get(chave) == colunas_do_arquivo:
                del resultado[chave]


def _falhou(resultado: Any) -> bool:
    """True se o resultado de uma operação sobre um arquivo é um erro."""
    return isinstance(resultado, dict) and (resultado.get("sucesso") is False or "erro" in resultado)


def _somar_distribuicao_por_turno(resultados: List[Dict[str, Any]], chave_lista: str) -> Dict[str, int]:
    """Soma, turno a turno, a quantidade de vários arquivos. Devolve {nome do turno: quantidade total}."""
    totais = {}
    for indice in range(4):
        totais[FAIXAS_HORARIAS[indice]["nome"]] = 0

    for resultado in resultados:
        if chave_lista == "distribuicao_por_turno":
            for nome_turno, quantidade in resultado["distribuicao_por_turno"].items():
                totais[nome_turno] += quantidade
        elif chave_lista == "contagem_por_turno":
            for nome_turno, dados in resultado["contagem_por_turno"].items():
                totais[nome_turno] += dados["quantidade"]
        else:  # dados_turno
            for dados in resultado["dados_turno"]:
                totais[dados["Turno"]] += dados["Quantidade"]
    return totais


def _total_geral(operation: str, resultados_ok: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Soma, em código, os resultados de vários arquivos (o modelo não precisa somar de cabeça).
    Só vale para operações que SOMAM: contagens, somas e distribuições por turno.
    Valores distintos, rankings e estatísticas não podem ser somados arquivo a arquivo, então ficam de fora.
    """
    if operation == "contar_linhas":
        return {"linhas": sum(r["linhas"] for r in resultados_ok)}

    if operation == "contar_por_valor":
        return {"total_linhas": sum(r["total_linhas"] for r in resultados_ok)}

    if operation == "agrupar_e_somar":
        return {
            "total_linhas": sum(r["total_linhas"] for r in resultados_ok),
            "soma_total": sum(r["soma_total"] for r in resultados_ok),
        }

    if operation not in ("filtrar_por_turno", "contar_por_turno", "comparar_por_turno"):
        return None

    total_transacoes = sum(r["total_transacoes"] for r in resultados_ok)
    geral: Dict[str, Any] = {"total_transacoes": total_transacoes}

    if operation == "filtrar_por_turno":
        if all(r.get("turno") == "todos" for r in resultados_ok):
            geral["distribuicao_por_turno"] = _somar_distribuicao_por_turno(resultados_ok, "distribuicao_por_turno")
        return geral

    # contar_por_turno e comparar_por_turno: quantidade e porcentagem de cada turno, no total
    chave = "contagem_por_turno" if operation == "contar_por_turno" else "dados_turno"
    quantidades = _somar_distribuicao_por_turno(resultados_ok, chave)

    por_turno = {}
    turno_com_mais, maior_quantidade = None, 0
    for indice in range(4):
        info = FAIXAS_HORARIAS[indice]
        quantidade = quantidades[info["nome"]]
        if quantidade == 0:
            continue
        porcentagem = round((quantidade / total_transacoes) * 100, 2)
        por_turno[info["nome"]] = {"quantidade": quantidade, "intervalo": info["intervalo"], "porcentagem": porcentagem}
        if quantidade > maior_quantidade:
            turno_com_mais, maior_quantidade = info["nome"], quantidade

    if operation == "contar_por_turno":
        geral["contagem_por_turno"] = por_turno
        geral["turno_com_mais_uso"] = turno_com_mais
    else:
        geral["dados_turno"] = [
            {"Turno": nome, "Quantidade": d["quantidade"], "Intervalo": d["intervalo"], "Porcentagem": d["porcentagem"]}
            for nome, d in por_turno.items()
        ]
    return geral


def _checar_parametros(operation: str, coluna, valor, coluna_soma, coluna_alvo=None) -> Optional[Dict[str, Any]]:
    """Erro autoexplicativo se faltar parâmetro obrigatório da operação; None se estiver tudo certo."""
    campos = {"coluna": coluna, "valor": valor, "coluna_soma": coluna_soma, "coluna_alvo": coluna_alvo}

    faltam = []
    for nome_campo in _EXIGIDOS.get(operation, ()):
        if campos[nome_campo] in (None, ""):
            faltam.append(nome_campo)

    if faltam:
        return {
            "erro": f"A operação '{operation}' exige o(s) parâmetro(s): {', '.join(faltam)}",
            "exemplo": _EXEMPLOS[operation],
            "dica": "Se não souber o nome da coluna, use 'mostrar_colunas' ou 'preview' antes.",
            "sucesso": False,
        }

    # Nas operações com filtro opcional, 'coluna' e 'valor' vêm juntos ou nenhum dos dois
    coluna_vazia = coluna in (None, "")
    valor_vazio = valor in (None, "")
    if operation in _OPERACOES_COM_FILTRO_OPCIONAL and coluna_vazia != valor_vazio:
        return {
            "erro": f"Em '{operation}', 'coluna' e 'valor' (filtro opcional) devem ser informados juntos",
            "exemplo": {"operation": operation, "coluna": "Descrição da Aplicação", "valor": "Idoso"},
            "sucesso": False,
        }
    return None


# ============================================================
# A TOOL
# ============================================================

@tool("analisar_dados_arquivo", args_schema=AnalisarArgs)
def analisar_dados_arquivo(
    package_id: str,
    operation: str = "contar_linhas",
    file_filter: str = "",
    coluna: Optional[str] = None,
    valor: Optional[str] = None,
    coluna_soma: Optional[str] = None,
    coluna_alvo: Optional[str] = None,
    coluna_data: Optional[str] = None,
    turno: Optional[str] = None,
    limite: Optional[int] = None,
    offset: int = 0,
    consulta_tipo: str = "atual",
    ano: Optional[int] = None,
    coluna_tarifa: Optional[str] = None,
    coluna_descricao: Optional[str] = None,
    linha_cabecalho: Optional[int] = None,
) -> Any:
    """
    Executa operações de análise em arquivos já baixados/processados.

    Operações (parâmetros além de package_id, file_filter e operation):
      - contar_linhas, mostrar_colunas, preview: sem parâmetros extras
      - media, soma, max, min: estatística de TODAS as colunas numéricas, sem parâmetros extras
      - valores_unicos: lista valores de uma coluna. Usa coluna (+ limite, offset)
      - agrupar_valores_unicos: ranking de ocorrências por valor. Usa coluna. Devolve o top 10; para ver mais,
        chame de novo com offset (+ limite, máx. 100), só se o usuário pedir
      - contar_por_valor: conta LINHAS em que a coluna contém o valor. Usa coluna, valor
      - contar_unicos: conta valores DISTINTOS (ex: quantos carros/linhas diferentes). Usa coluna_alvo
        (+ coluna, valor como filtro opcional, ex: só do sindicato X)
      - agrupar_e_somar: filtra coluna=valor e SOMA outra coluna (totais). Usa coluna, valor, coluna_soma
      - filtrar_por_turno: transações de um turno. Usa turno (+ coluna, valor como filtro opcional; coluna_data)
      - contar_por_turno: distribuição por turno e turno de maior uso. Usa coluna, valor (opcionais), coluna_data
      - comparar_por_turno: distribuição por turno para gráficos. Usa coluna, valor (opcionais), coluna_data
      - leitura_tarifa: tarifas históricas. Usa consulta_tipo, ano. Informe também coluna_tarifa, coluna_data
        (início da vigência) e, se existir, coluna_descricao (ex.: a linha ou o tipo da tarifa); se o cabeçalho não
        for a primeira linha, informe linha_cabecalho. Sem isso, as colunas são inferidas (e o retorno avisa).

    Com vários arquivos, o retorno traz um resultado por arquivo e, para contagens e somas, o `total_geral`
    em `_resumo_analise`. Use o `total_geral`; não some os arquivos de cabeça.

    Exemplo: {"package_id": "setram_sbe", "file_filter": "consolidado_2026_08", "operation": "agrupar_e_somar",
              "coluna": "Modal Operadora", "valor": "ÔNIBUS", "coluna_soma": "Qtd. Transações"}
    """

    try:
        turno = turno if turno not in (None, "") else "todos"

        erro_parametros = _checar_parametros(operation, coluna, valor, coluna_soma, coluna_alvo)
        if erro_parametros:
            logger.error(
                f"{erro_parametros['erro']} | recebido: coluna={coluna!r}, valor={valor!r}, "
                f"coluna_soma={coluna_soma!r}, coluna_alvo={coluna_alvo!r}"
            )
            return erro_parametros

        logger.info("ANALISAR_DADOS_ARQUIVO - INÍCIO")
        logger.info(f"package_id: {package_id}")
        logger.info(f"file_filter: {file_filter}")
        logger.info(f"operation: {operation}")

        if not package_id:
            return {
                "erro": "Parâmetro 'package_id' é obrigatório.",
                "sucesso": False,
            }

        logger.info("Obtendo arquivos para análise...")
        resultado_obtencao = obter_arquivos_para_analise(
            package_id=package_id,
            file_filter=file_filter,
            força_download=False,
        )

        if not resultado_obtencao.get("sucesso"):
            erro = resultado_obtencao.get("erro", "Erro desconhecido")
            logger.error(f"Erro ao obter arquivos: {erro}")
            return {
                "erro": erro,
                "sucesso": False,
            }

        arquivos_para_analisar = resultado_obtencao.get("arquivos", [])
        logger.info(f"{len(arquivos_para_analisar)} arquivo(s) obtido(s)")

        parametros = Parametros(
            operacao=operation, coluna=coluna, valor=valor, coluna_soma=coluna_soma, coluna_alvo=coluna_alvo,
            coluna_data=coluna_data, turno=turno, limite=limite, offset=offset, consulta_tipo=consulta_tipo,
            ano=ano, coluna_tarifa=coluna_tarifa, coluna_descricao=coluna_descricao,
            linha_cabecalho=linha_cabecalho,
        )

        funcao_da_operacao = _OPERACOES.get(operation)
        if funcao_da_operacao is None:
            logger.error(f"Operação '{operation}' não reconhecida")
            return {
                "erro": f"Operação desconhecida: {operation}",
                "operacoes_disponiveis": list(get_args(Operacao)),
                "sucesso": False,
            }

        # ---------- Roda a operação em cada arquivo ----------
        resultados: Dict[str, Any] = {}
        arquivos_analisados = 0
        arquivos_com_erro = 0

        for arquivo in arquivos_para_analisar:
            nome = arquivo["nome"]
            df = arquivo["df"]

            logger.info(f"ANALISANDO: {nome}")
            logger.info(f"Shape: {df.shape} (linhas x colunas)")
            logger.info(f"Colunas: {list(df.columns)}")

            try:
                resultados[nome] = funcao_da_operacao(arquivo, parametros)
            except Exception as e:
                # O detalhe completo vai para o log; o modelo recebe só a mensagem curta
                logger.error(f"Erro ao analisar arquivo {nome}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                resultados[nome] = {
                    "erro": f"Erro ao analisar arquivo {nome}: {str(e)}",
                    "sucesso": False,
                }

            if _falhou(resultados[nome]):
                arquivos_com_erro += 1
                logger.warning(f"Operação '{operation}' falhou em {nome}: {resultados[nome].get('erro')}")
            else:
                arquivos_analisados += 1
                logger.info(f"Operação '{operation}' concluída com sucesso")

        # ---------- Resumo ----------
        try:
            resumo = {
                "pasta_temporaria": obter_pasta_temporaria(),
                "arquivos_analisados": arquivos_analisados,
                "arquivos_com_erro": arquivos_com_erro,
                "operacao_executada": operation,
                "sucesso_geral": arquivos_analisados > 0,
            }

            if operation not in ("mostrar_colunas", "preview"):  # estas já devolvem as colunas
                resumo.update(_esquemas(arquivos_para_analisar))
                _remover_colunas_repetidas(resultados, arquivos_para_analisar)

            # Total geral: só quando mais de um arquivo deu certo
            resultados_ok = []
            for arquivo in arquivos_para_analisar:
                if not _falhou(resultados.get(arquivo["nome"])):
                    resultados_ok.append(resultados[arquivo["nome"]])

            if len(resultados_ok) > 1:
                total_geral = _total_geral(operation, resultados_ok)
                if total_geral is not None:
                    total_geral["arquivos_somados"] = len(resultados_ok)
                    if arquivos_com_erro:
                        total_geral["atencao"] = f"{arquivos_com_erro} arquivo(s) com erro ficaram de fora da soma"
                    resumo["total_geral"] = total_geral

            if resultado_obtencao.get("aviso"):
                resumo["aviso"] = resultado_obtencao["aviso"]

            resultados["_resumo_analise"] = resumo
            logger.info(f"RESUMO: {arquivos_analisados} arquivo(s) analisado(s), {arquivos_com_erro} com erro")

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

        return resultados

    except Exception as e:
        error_msg = f"Falha geral na análise: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        return {
            "erro": error_msg,
            "sucesso": False,
        }
