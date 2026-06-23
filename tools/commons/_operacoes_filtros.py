"""
Operações de filtragem e agregação de dados.
Cada função cuida do seu próprio log/debug. As operações são do escopo de analisar_dados_arquivo.py

- executar_contar_por_valor: conta linhas que contêm determinado valor
- executar_agrupar_e_somar: filtra por valor e soma coluna numérica
"""

import pandas as pd
from typing import Any, Dict
import unicodedata  

def _normalizar_texto(texto: str) -> str:
    """Remove acentos e normaliza para comparação"""
    if not isinstance(texto, str):
        return str(texto).lower().strip()
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = ''.join(c for c in nfkd if not unicodedata.category(c).startswith('M'))
    return sem_acento.lower().strip()

def _log_inicio(nome_operacao: str, **kwargs):
    """Log padronizado no início de cada operação."""
    print(f"\n🔍 {nome_operacao}:")
    for chave, valor in kwargs.items():
        print(f"   {chave}: {valor}")


def executar_contar_por_valor(
    df: pd.DataFrame,
    coluna: str,
    valor: str,
    arquivo_local: str
) -> Dict[str, Any]:
    """
    Conta quantas linhas contêm determinado valor em uma coluna.
    Busca parcial e case-insensitive (str.contains).

    Args:
        df: DataFrame a analisar
        coluna: Nome da coluna para filtrar
        valor: Valor a buscar (parcial, case-insensitive)
        arquivo_local: Caminho do arquivo

    Returns:
        Dict com total de linhas e valores encontrados
    """

    _log_inicio(
        "CONTAR_POR_VALOR (conta linhas)",
        Coluna=coluna,
        Valor_procurado=valor
    )

    # ============================================================
    # Validação de parâmetros
    # ============================================================

    if not coluna or valor is None:
        print(f"❌ Parâmetros faltando")
        return {
            "erro": "Parâmetros 'column' e 'value' são obrigatórios",
            "sucesso": False,
        }

    if coluna not in df.columns:
        print(f"❌ Coluna '{coluna}' não existe")
        return {
            "erro": f"Coluna '{coluna}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    # ============================================================
    # Busca parcial case-insensitive (str.contains)
    # Ex: "Idoso" ENCONTRA "7001 - Idoso" ✅
    # Ex: "7001" ENCONTRA "7001 - Idoso" ✅
    # Ex: "idoso" ENCONTRA "7001 - Idoso" ✅ (case-insensitive)
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

    print(f"\n   🔢 RESULTADO: {total_linhas} linhas encontradas")
    if valores_encontrados:
        print(f"   📋 Valores correspondentes: {valores_encontrados}")

    return {
        "coluna": coluna,
        "valor_buscado": valor,
        "valores_encontrados": valores_encontrados,
        "total_linhas": int(total_linhas),
        "arquivo_local": arquivo_local,
        "sucesso": True,
    }


def executar_agrupar_e_somar(
    df: pd.DataFrame,
    filter_column: str,
    filter_value: str,
    sum_column: str,
    arquivo_local: str
) -> Dict[str, Any]:
    """
    Filtra por valor em uma coluna e soma outra coluna numérica.
    Busca parcial e case-insensitive.

    Args:
        df: DataFrame a analisar
        filter_column: Coluna para filtrar (ex: "TIPO_GRATUIDADE")
        filter_value: Valor a filtrar (ex: "Idoso")
        sum_column: Coluna numérica para somar (ex: "QUANTIDADE_TRANSACAO")
        arquivo_local: Caminho do arquivo

    Returns:
        Dict com total de linhas, soma e valores encontrados
    """

    _log_inicio(
        "AGRUPAR_E_SOMAR",
        Filtrar_coluna=filter_column,
        Filtrar_valor=filter_value,
        Somar_coluna=sum_column
    )

    # ============================================================
    # Validação de parâmetros
    # ============================================================

    if not filter_column or filter_value is None:
        print(f"❌ Parâmetros de filtro faltando")
        return {
            "erro": "Parâmetros 'filter_column' e 'filter_value' são obrigatórios",
            "sucesso": False,
        }

    if not sum_column:
        print(f"❌ Falta sum_column")
        return {
            "erro": "Parâmetro 'sum_column' é obrigatório",
            "exemplo": "sum_column='QUANTIDADE_TRANSACAO'",
            "sucesso": False,
        }

    if filter_column not in df.columns:
        print(f"❌ Coluna '{filter_column}' não existe")
        return {
            "erro": f"Coluna de filtro '{filter_column}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    if sum_column not in df.columns:
        print(f"❌ Coluna '{sum_column}' não existe")
        return {
            "erro": f"Coluna a somar '{sum_column}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }

    # ============================================================
    # Filtrar dados
    # ============================================================

    valores_unicos = df[filter_column].unique()
    print(f"\n   📊 Valores únicos em '{filter_column}': {list(valores_unicos)[:10]}")

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

    print(f"\n   📊 Linhas filtradas: {total_linhas}")
    if valores_encontrados:
        print(f"   ✅ Valores correspondentes: {valores_encontrados}")

    # ============================================================
    # Sem resultados
    # ============================================================

    if total_linhas == 0:
        print(f"   ⚠️ NENHUMA linha corresponde ao valor '{filter_value}'")
        print(f"   Valores disponíveis: {list(valores_unicos)[:10]}")

        return {
            "filter_column": filter_column,
            "filter_value": filter_value,
            "sum_column": sum_column,
            "total_linhas": 0,
            "soma_total": 0,
            "valores_disponiveis": list(valores_unicos),
            "sucesso": True,
        }

    # ============================================================
    # Somar coluna numérica
    # ============================================================

    if sum_column not in df_filtrado.select_dtypes(include=["number"]).columns:
        print(f"   ❌ Coluna '{sum_column}' não é numérica")
        return {
            "erro": f"Coluna '{sum_column}' não é numérica",
            "tipo_coluna": str(df[sum_column].dtype),
            "sucesso": False,
        }

    soma_total = df_filtrado[sum_column].sum()
    print(f"   ✅ Soma de '{sum_column}': {soma_total:,.0f}")
    print(f"\n   Primeiras linhas filtradas:")
    print(df_filtrado[[filter_column, sum_column]].head())

    return {
        "filter_column": filter_column,
        "filter_value": filter_value,
        "valores_encontrados": valores_encontrados,
        "sum_column": sum_column,
        "total_linhas": int(total_linhas),
        "soma_total": float(soma_total),
        "arquivo_local": arquivo_local,
        "sucesso": True,
    }