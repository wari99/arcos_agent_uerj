"""
Operações de filtragem e agregação de dados.
Cada função cuida do seu próprio log/debug. As operações são do escopo de analisar_dados_arquivo.py

- executar_contar_por_valor: conta linhas que contêm determinado valor
- executar_agrupar_e_somar: filtra por valor e soma coluna numérica
- executar_agrupar_valores_unicos: conta quantas vezes cada valor único de uma coluna aparece
"""

import pandas as pd
from typing import Any, Dict
import unicodedata
import logging

logger = logging.getLogger(__name__)

def _normalizar_texto(texto: str) -> str:
    """Remove acentos e normaliza para comparação"""
    if not isinstance(texto, str):
        return str(texto).lower().strip()
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = ''.join(c for c in nfkd if not unicodedata.category(c).startswith('M'))
    return sem_acento.lower().strip()


def _log_inicio(nome_operacao: str, **kwargs):
    """Log padronizado no início de cada operação."""
    logger.info(f"{nome_operacao}")
    for chave, valor in kwargs.items():
        logger.info(f"   {chave}: {valor}")


def executar_contar_por_valor(
    df: pd.DataFrame,
    coluna: str,
    valor: str,
    path: str
) -> Dict[str, Any]:
    """
    Conta quantas linhas contêm determinado valor em uma coluna.
    Busca parcial e case-insensitive (str.contains).

    Args:
        df: DataFrame a analisar
        coluna: Nome da coluna para filtrar
        valor: Valor a buscar (parcial, case-insensitive)
        path: Caminho do arquivo

    Returns:
        Dict com total de linhas e valores encontrados
    """

    _log_inicio(
        "CONTAR_POR_VALOR (conta linhas)",
        Coluna=coluna,
        Valor_procurado=valor
    )

    if not coluna or valor is None:
        logger.error("Parâmetros faltando")
        return {
            "erro": "Parâmetros 'column' e 'value' são obrigatórios",
            "sucesso": False,
        }

    if coluna not in df.columns:
        logger.error(f"Coluna '{coluna}' não existe")
        return {
            "erro": f"Coluna '{coluna}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    # ============================================================
    # Busca parcial case-insensitive (str.contains)
    # Ex: "Idoso" ENCONTRA "7001 - Idoso" 
    # Ex: "7001" ENCONTRA "7001 - Idoso" 
    # Ex: "idoso" ENCONTRA "7001 - Idoso" 
    # ============================================================

    #df_filtrado = df[
    #    df[coluna]
    #    .astype(str)
    #    .str.contains(str(valor), case=False, na=False)
    #]

    valor_normalizado = _normalizar_texto(str(valor))
    df_filtrado = df[
        df[coluna]
        .astype(str)
        .apply(lambda x: valor_normalizado in _normalizar_texto(x))
    ]

    total_linhas = len(df_filtrado)

    valores_encontrados = (
        df_filtrado[coluna].unique().tolist() if total_linhas > 0 else []
    )

    logger.info(f"RESULTADO: {total_linhas} linhas encontradas")
    if valores_encontrados:
        logger.info(f"Valores correspondentes: {valores_encontrados}")

    return {
        "coluna": coluna,
        "valor_buscado": valor,
        "valores_encontrados": valores_encontrados,
        "total_linhas": int(total_linhas),
        "path": path,
        "sucesso": True,
    }


def executar_agrupar_e_somar(
    df: pd.DataFrame,
    filter_column: str,
    filter_value: str,
    sum_column: str,
    path: str
) -> Dict[str, Any]:
    """
    Filtra por valor em uma coluna e soma outra coluna numérica.
    Busca parcial e case-insensitive.

    Args:
        df: DataFrame a analisar
        filter_column: Coluna para filtrar (ex: "TIPO_GRATUIDADE")
        filter_value: Valor a filtrar (ex: "Idoso")
        sum_column: Coluna numérica para somar (ex: "QUANTIDADE_TRANSACAO")
        path: Caminho do arquivo

    Returns:
        Dict com total de linhas, soma e valores encontrados
    """

    _log_inicio(
        "AGRUPAR_E_SOMAR",
        Filtrar_coluna=filter_column,
        Filtrar_valor=filter_value,
        Somar_coluna=sum_column
    )

    if not filter_column or filter_value is None:
        logger.error("Parâmetros de filtro faltando")
        return {
            "erro": "Parâmetros 'filter_column' e 'filter_value' são obrigatórios",
            "sucesso": False,
        }

    if not sum_column:
        logger.error("Falta sum_column")
        return {
            "erro": "Parâmetro 'sum_column' é obrigatório",
            "exemplo": "sum_column='QUANTIDADE_TRANSACAO'",
            "sucesso": False,
        }

    if filter_column not in df.columns:
        logger.error(f"Coluna '{filter_column}' não existe")
        return {
            "erro": f"Coluna de filtro '{filter_column}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    if sum_column not in df.columns:
        logger.error(f"Coluna '{sum_column}' não existe")
        return {
            "erro": f"Coluna a somar '{sum_column}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    valores_unicos = df[filter_column].unique()
    logger.info(f"Valores únicos em '{filter_column}': {list(valores_unicos)[:10]}")

    #df_filtrado = df[
    #    df[filter_column]
    #    .astype(str)
    #    .str.contains(str(filter_value), case=False, na=False)
    #]
    valor_normalizado = _normalizar_texto(str(filter_value))
    df_filtrado = df[
        df[filter_column]
        .astype(str)
        .apply(lambda x: valor_normalizado in _normalizar_texto(x))
    ]
    total_linhas = len(df_filtrado)

    valores_encontrados = (
        df_filtrado[filter_column].unique().tolist() if total_linhas > 0 else []
    )

    logger.info(f"Linhas filtradas: {total_linhas}")
    if valores_encontrados:
        logger.info(f"Valores correspondentes: {valores_encontrados}")

    if total_linhas == 0:
        logger.warning(f"NENHUMA linha corresponde ao valor '{filter_value}'")
        logger.info(f"Valores disponíveis: {list(valores_unicos)[:10]}")

        return {
            "filter_column": filter_column,
            "filter_value": filter_value,
            "sum_column": sum_column,
            "total_linhas": 0,
            "soma_total": 0,
            "valores_disponiveis": list(valores_unicos),
            "sucesso": True,
        }

    # somar de coluna numérica
    if sum_column not in df_filtrado.select_dtypes(include=["number"]).columns:
        logger.error(f"Coluna '{sum_column}' não é numérica")
        return {
            "erro": f"Coluna '{sum_column}' não é numérica",
            "tipo_coluna": str(df[sum_column].dtype),
            "sucesso": False,
        }

    soma_total = df_filtrado[sum_column].sum()
    logger.info(f"Soma de '{sum_column}': {soma_total:,.0f}")
    logger.debug(f"Primeiras linhas filtradas:\n{df_filtrado[[filter_column, sum_column]].head()}")

    return {
        "filter_column": filter_column,
        "filter_value": filter_value,
        "valores_encontrados": valores_encontrados,
        "sum_column": sum_column,
        "total_linhas": int(total_linhas),
        "soma_total": float(soma_total),
        "path": path,
        "sucesso": True,
    }


def executar_agrupar_valores_unicos(
    df: pd.DataFrame,
    coluna_grupo: str,
    path: str = None
) -> Dict[str, Any]:
    """
    Conta quantas vezes cada valor único aparece em uma coluna.
    Perfeito quando cada transação vale 1 ponto.

    Args:
        df: DataFrame a analisar
        coluna_grupo: Coluna com valores únicos (ex: "LINHA")
        path: Caminho do arquivo

    Returns:
        Dict com ranking completo, top 10, e estatísticas
    """
    if not coluna_grupo:
        logger.error("Parâmetro 'coluna_grupo' faltando")
        return {
            "erro": "Parâmetro 'coluna_grupo' é obrigatório",
            "sugestao": "Você deve informar qual coluna deseja agrupar",
            "exemplo": "coluna_grupo='Linha'",
            "sucesso": False,
        }

    if coluna_grupo not in df.columns:
        logger.error(f"Coluna '{coluna_grupo}' não encontrada")
        return {
            "erro": f"Coluna '{coluna_grupo}' não existe neste arquivo",
            "coluna_fornecida": coluna_grupo,
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    _log_inicio(
        "AGRUPAR_VALORES_UNICOS (COUNT)",
        Coluna_grupo=coluna_grupo,
        Total_registros=len(df),
        Valores_unicos=df[coluna_grupo].nunique()
    )

    logger.info("Contando ocorrências de cada valor único...")

    contagem = df[coluna_grupo].value_counts().to_dict()

    total_grupos = len(contagem)
    soma_total = sum(contagem.values())
    media = soma_total / total_grupos if total_grupos > 0 else 0

    ranking = sorted(
        contagem.items(),
        key=lambda x: x[1],
        reverse=True
    )

    logger.info(f"{total_grupos} grupos únicos encontrados")
    logger.info(f"Total de transações: {soma_total:,}")
    logger.info(f"Média por grupo: {media:.2f}")

    logger.info("TOP 10:")
    for i, (grupo, count) in enumerate(ranking[:10], 1):
        percentual = (count / soma_total * 100) if soma_total > 0 else 0
        logger.info(f"   {i}º - {grupo}: {count:,} ({percentual:.2f}%)")

    return {
        "coluna_grupo": coluna_grupo,
        "operacao": "contagem",
        "total_grupos": int(total_grupos),
        "soma_total": int(soma_total),
        "media_por_grupo": round(media, 2),
        "top_10": [
            {
                "posicao": i + 1,
                "grupo": grupo,
                "total": int(count),
                "percentual": round((count / soma_total * 100) if soma_total > 0 else 0, 2)
            }
            for i, (grupo, count) in enumerate(ranking[:10])
        ],
        "ranking_completo": [
            {"grupo": grupo, "total": int(count)}
            for grupo, count in ranking
        ],
        "path": path,
        "sucesso": True,
    }