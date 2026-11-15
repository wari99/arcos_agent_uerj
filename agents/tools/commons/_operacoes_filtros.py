"""
Operações de filtragem e agregação de dados.
Cada função cuida do seu próprio log/debug. As operações são do escopo de analisar_dados_arquivo.py

Operações (as funções que começam com "executar_"):
- executar_contar_por_valor: conta linhas que contêm determinado valor
- executar_contar_unicos: conta valores distintos de uma coluna (com filtro opcional por valor)
- executar_agrupar_e_somar: filtra por valor e soma coluna numérica
- executar_agrupar_valores_unicos: ranking de quantas vezes cada valor aparece (paginado)

Como ler este arquivo:
1. As funções de apoio de coluna e de filtro ficam em _apoio_colunas.py (usadas também pelas outras operações).
2. Aqui vêm as quatro operações. Todas seguem a mesma ordem:
   (a) registrar no log o que foi pedido,
   (b) conferir se os parâmetros e as colunas existem,
   (c) fazer o cálculo,
   (d) devolver um dicionário com o resultado ("sucesso": True) ou com o erro ("sucesso": False).
"""

import logging
from typing import Any, Dict, Tuple

import pandas as pd

from agents.tools.commons._apoio_colunas import (
    filtrar_por_valor,
    sugerir_valores,
    validar_coluna,
)

logger = logging.getLogger(__name__)

LIMITE_PADRAO_RANKING = 10 # default, retorna top 10
LIMITE_MAXIMO_RANKING = 100 # limite para preservar o contexto

# ============================================================
# FUNÇÃO DE APOIO: LOG
# (as funções de coluna e de filtro ficam em _apoio_colunas.py, compartilhadas com as outras operações)
# ============================================================

def _log_inicio(nome_operacao: str, **parametros):
    """
    Registra no log o começo de uma operação, no formato:
    NOME_DA_OPERACAO | parametro1=valor1 | parametro2=valor2
    """
    partes = []
    for nome_parametro, valor in parametros.items():
        partes.append(f"{nome_parametro}={valor}")

    detalhes = " | ".join(partes)
    logger.info(f"{nome_operacao} | {detalhes}")

def executar_contar_por_valor( # operacao: contar linhas que contem determinado valor
    df: pd.DataFrame,
    coluna: str,
    valor: str,
    path: str
) -> Dict[str, Any]:
    """
    Conta quantas linhas contêm determinado valor em uma coluna. Busca parcial, sem acento e sem diferenciar maiúsculas.
    Ex: "Idoso", "7001" e "idoso" encontram "7001 - Idoso".

    Args:
        df: DataFrame a analisar
        coluna: Nome da coluna para filtrar
        valor: Valor a buscar (parcial, case-insensitive)
        path: Caminho do arquivo

    Returns:
        Dict com total de linhas e valores encontrados
    """

    _log_inicio("CONTAR_POR_VALOR (conta linhas)", Coluna=coluna, Valor_procurado=valor)

    if not coluna or valor is None:
        logger.error("Parâmetros faltando")
        return {
            "erro": "Parâmetros 'column' e 'value' são obrigatórios",
            "sucesso": False,
        }

    coluna, erro = validar_coluna(df, coluna, "Coluna '{}' não encontrada")
    if erro:
        return erro

    df_filtrado, _ = filtrar_por_valor(df, coluna, valor)
    total_linhas = len(df_filtrado)
    valores_encontrados = df_filtrado[coluna].unique().tolist()

    logger.info(f"RESULTADO: {total_linhas} linhas encontradas | valores correspondentes: {valores_encontrados}")

    return {
        "coluna": coluna,
        "valor_buscado": valor,
        "valores_encontrados": valores_encontrados,
        "total_linhas": total_linhas,
        "path": path,
        "sucesso": True,
    }

def executar_contar_unicos( # operacao: contar valores unicos em uma coluna
    df: pd.DataFrame,
    coluna_alvo: str,
    path: str,
    coluna: str = None,
    valor: str = None,
) -> Dict[str, Any]:
    """
    Conta quantos valores DISTINTOS existem em coluna_alvo, opcionalmente só nas linhas em que coluna contém valor (busca parcial, sem acento e sem diferenciar maiúsculas).

    Args:
        df: DataFrame a analisar
        coluna_alvo: Coluna cujos valores distintos serão contados (ex: "Nº Carro")
        path: Caminho do arquivo
        coluna: Coluna do filtro opcional (ex: "Sindicato")
        valor: Valor do filtro opcional (ex: "SINTERJ")

    Returns:
        Dict com a quantidade de valores distintos, o total de linhas consideradas e uma amostra dos valores
    """

    _log_inicio("CONTAR_UNICOS", Coluna_alvo=coluna_alvo, Filtro_coluna=coluna, Filtro_valor=valor)

    if not coluna_alvo:
        return {
            "erro": "Parâmetro 'coluna_alvo' é obrigatório",
            "exemplo": {"operation": "contar_unicos", "coluna_alvo": "Nº Carro", "coluna": "Sindicato", "valor": "SINTERJ"},
            "sucesso": False,
        }

    coluna_vazia = coluna in (None, "")
    valor_vazio = valor in (None, "")
    if coluna_vazia != valor_vazio:
        return {
            "erro": "'coluna' e 'valor' (filtro opcional) devem ser informados juntos",
            "sucesso": False,
        }

    coluna_alvo, erro = validar_coluna(df, coluna_alvo, "Coluna '{}' não encontrada")
    if erro:
        return erro

    coluna, erro = validar_coluna(df, coluna, "Coluna '{}' não encontrada")
    if erro:
        return erro

    if coluna:
        df_filtrado, valores_do_filtro = filtrar_por_valor(df, coluna, valor)
    else:
        df_filtrado = df
        valores_do_filtro = []

    total_linhas = len(df_filtrado)

    unicos = df_filtrado[coluna_alvo].dropna().unique()

    mensagem_log = f"Linhas consideradas: {total_linhas} | distintos em '{coluna_alvo}': {len(unicos)}"
    if valores_do_filtro:
        mensagem_log += f" | valores do filtro: {valores_do_filtro}"
    logger.info(mensagem_log)

    amostra_valores = []
    for valor_unico in unicos[:10]:
        if hasattr(valor_unico, "item"):
            amostra_valores.append(valor_unico.item())
        else:
            amostra_valores.append(valor_unico)

    resultado = {
        "coluna_alvo": coluna_alvo,
        "quantidade_unicos": len(unicos),
        "total_linhas_consideradas": total_linhas,
        "amostra_valores": amostra_valores,
        "path": path,
        "sucesso": True,
    }

    if coluna:
        resultado["filtro"] = {
            "coluna": coluna,
            "valor": valor,
            "valores_encontrados": valores_do_filtro,
        }
        if total_linhas == 0:
            resultado["aviso"] = f"Nenhuma linha em '{coluna}' corresponde a '{valor}'"

    return resultado

def executar_agrupar_e_somar( # operacao: filtra por um valor e soma outra coluna numérica
    df: pd.DataFrame,
    coluna: str,
    valor: str,
    coluna_soma: str,
    path: str
) -> Dict[str, Any]:
    """
    Filtra por valor em uma coluna e soma outra coluna numérica. Busca parcial e case-insensitive.

    Args:
        df: DataFrame a analisar
        coluna: Coluna para filtrar (ex: "TIPO_GRATUIDADE")
        valor: Valor a filtrar (ex: "Idoso")
        coluna_soma: Coluna numérica para somar (ex: "QUANTIDADE_TRANSACAO")
        path: Caminho do arquivo

    Returns:
        Dict com total de linhas, soma e valores encontrados
    """

    _log_inicio("AGRUPAR_E_SOMAR", Filtrar_coluna=coluna, Filtrar_valor=valor, Somar_coluna=coluna_soma)

    if not coluna or valor is None:
        logger.error("Parâmetros de filtro faltando")
        return {
            "erro": "Parâmetros 'coluna' e 'valor' são obrigatórios",
            "sucesso": False,
        }

    if not coluna_soma:
        logger.error("Falta coluna_soma")
        return {
            "erro": "Parâmetro 'coluna_soma' é obrigatório",
            "exemplo": "coluna_soma='QUANTIDADE_TRANSACAO'",
            "sucesso": False,
        }

    coluna, erro = validar_coluna(df, coluna, "Coluna de filtro '{}' não encontrada")
    if erro:
        return erro

    coluna_soma, erro = validar_coluna(df, coluna_soma, "Coluna a somar '{}' não encontrada")
    if erro:
        return erro

    df_filtrado, _ = filtrar_por_valor(df, coluna, valor)
    total_linhas = len(df_filtrado)
    valores_encontrados = df_filtrado[coluna].unique().tolist()

    logger.info(f"Linhas filtradas: {total_linhas} | valores correspondentes: {valores_encontrados}")

    if total_linhas == 0:
        valores_unicos = df[coluna].unique()
        sugestoes = sugerir_valores(valores_unicos, valor)
        logger.warning(f"NENHUMA linha corresponde ao valor '{valor}'. Valores parecidos: {sugestoes}")

        return {
            "coluna": coluna,
            "valor": valor,
            "coluna_soma": coluna_soma,
            "total_linhas": 0,
            "soma_total": 0,
            "valores_disponiveis": sugestoes,
            "total_valores_distintos": len(valores_unicos),
            "sucesso": True,
        }

    colunas_numericas = df.iloc[:0].select_dtypes(include=["number"]).columns
    if coluna_soma not in colunas_numericas:
        logger.error(f"Coluna '{coluna_soma}' não é numérica")
        return {
            "erro": f"Coluna '{coluna_soma}' não é numérica",
            "tipo_coluna": str(df[coluna_soma].dtype),
            "sucesso": False,
        }

    soma_total = df_filtrado[coluna_soma].sum()
    logger.info(f"Soma de '{coluna_soma}': {soma_total:,.0f}")

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Primeiras linhas filtradas:\n{df_filtrado[[coluna, coluna_soma]].head()}")

    return {
        "coluna": coluna,
        "valor": valor,
        "valores_encontrados": valores_encontrados,
        "coluna_soma": coluna_soma,
        "total_linhas": total_linhas,
        "soma_total": float(soma_total),
        "path": path,
        "sucesso": True,
    }

def executar_agrupar_valores_unicos( # operacao: ranking de quantas vezes cada valor aparece (paginacao com limite e offset)
    df: pd.DataFrame,
    coluna: str,
    path: str = None,
    limite: int = LIMITE_PADRAO_RANKING,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Conta quantas vezes cada valor único aparece em uma coluna e devolve o ranking paginado. Ideal quando cada transação vale 1 ponto.

    Por padrão devolve só o top 10. Para ver mais, chamar de novo com `offset` (ex.: offset=10 traz do 11º ao 20º). Cada chamada devolve no máximo LIMITE_MAXIMO_RANKING itens.

    Args:
        df: DataFrame a analisar
        coluna: Coluna com valores únicos (ex: "LINHA")
        path: Caminho do arquivo
        limite: Quantos itens do ranking devolver (padrão 10, máximo 100)
        offset: Quantos itens pular (0 = começa no 1º lugar)

    Returns:
        Dict com a página do ranking, estatísticas gerais e como pedir a próxima página
    """

    if not coluna:
        logger.error("Parâmetro 'coluna' faltando")
        return {
            "erro": "Parâmetro 'coluna' é obrigatório",
            "sugestao": "Você deve informar qual coluna deseja agrupar",
            "exemplo": "coluna='Linha'",
            "sucesso": False,
        }

    coluna_fornecida = coluna
    coluna, erro = validar_coluna(
        df, coluna, "Coluna '{}' não existe neste arquivo", coluna_fornecida=coluna_fornecida
    )
    if erro:
        return erro

    try:
        if limite is None:
            limite = LIMITE_PADRAO_RANKING
        else:
            limite = int(limite)

        if offset:
            offset = int(offset)
        else:
            offset = 0
    except (ValueError, TypeError):
        return {
            "erro": f"Parâmetros inválidos: limite={limite}, offset={offset}",
            "instrucoes": "limite e offset devem ser números inteiros",
            "sucesso": False,
        }

    if limite < 1 or offset < 0:
        return {
            "erro": f"Parâmetros inválidos: limite={limite}, offset={offset}",
            "instrucoes": "limite deve ser >= 1 e offset >= 0",
            "sucesso": False,
        }

    aviso = None
    if limite > LIMITE_MAXIMO_RANKING:
        aviso = (
            f"limite={limite} reduzido para {LIMITE_MAXIMO_RANKING} (máximo por chamada); "
            f"use 'offset' para continuar de onde parou"
        )
        limite = LIMITE_MAXIMO_RANKING

    _log_inicio("AGRUPAR_VALORES_UNICOS (COUNT)", Coluna_grupo=coluna, Total_registros=len(df), Limite=limite, Offset=offset)

    contagem_por_valor = df[coluna].value_counts()
    contagem_ordenada = contagem_por_valor.sort_index().sort_values(ascending=False, kind="stable")
    ranking = list(contagem_ordenada.items())

    total_grupos = len(ranking)
    soma_total = 0

    for grupo, total in ranking:
        soma_total += total

    if total_grupos > 0:
        media = soma_total / total_grupos
    else:
        media = 0

    pagina = ranking[offset:offset + limite]

    itens = []
    posicao = offset + 1
    for grupo, total in pagina:
        if soma_total > 0:
            percentual = total / soma_total * 100
        else:
            percentual = 0

        itens.append({
            "posicao": posicao,
            "grupo": grupo,
            "total": int(total),
            "percentual": round(percentual, 2),
        })
        posicao += 1

    ultima_posicao_da_pagina = offset + len(pagina)
    tem_mais = ultima_posicao_da_pagina < total_grupos

    if total_grupos > 0 and offset >= total_grupos:
        aviso = f"offset={offset} está além do último grupo (total_grupos={total_grupos})"

    logger.info(f"{total_grupos} grupos únicos | total de transações: {soma_total:,} | média por grupo: {media:.2f}")
    for item in itens:
        logger.info(f"   {item['posicao']}º - {item['grupo']}: {item['total']:,} ({item['percentual']:.2f}%)")

    if itens:
        posicao_inicial = itens[0]["posicao"]
        posicao_final = itens[-1]["posicao"]
    else:
        posicao_inicial = None
        posicao_final = None

    if tem_mais:
        proximo_offset = ultima_posicao_da_pagina
    else:
        proximo_offset = None

    resultado = {
        "coluna": coluna,
        "operacao": "contagem",
        "total_grupos": total_grupos,
        "soma_total": int(soma_total),
        "media_por_grupo": round(media, 2),
        "posicao_inicial": posicao_inicial,
        "posicao_final": posicao_final,
        "tem_mais": tem_mais,
        "proximo_offset": proximo_offset,
        "ranking": itens,
    }

    if aviso:
        resultado["aviso"] = aviso

    resultado["path"] = path
    resultado["sucesso"] = True
    return resultado
