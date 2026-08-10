"""
Operações básicas de análise de dados. As operações são do escopo de analisar_dados_arquivo.py

- contar_linhas: operacao para contar o total de linhas de um dataframe
- mostrar_colunas: lista as colunas e tipos de dados nelas contidos
- preview: operacao para mostrar as 5 primeiras linhas de um df
- media, soma, max, min: operações nas colunas numéricas do df 
    {média dos valores, soma dos valores, valor máximo e valor mínimo presente em uma coluna}
"""

import pandas as pd
from typing import Dict, Any
from .core import logger

BYTES_TO_MB = 1024 * 1024

def executar_contar_linhas(df: pd.DataFrame, path: str) -> Dict[str, Any]:
    """
    Conta total de linhas no arquivo.
    
    Args:
        df: DataFrame a analisar
        path: Caminho do arquivo
    
    Returns:
        Dict com resultado da contagem
    """
    memoria_mb = df.memory_usage(deep=True).sum() / BYTES_TO_MB
    
    logger.info(f"Total: {len(df)} linhas")
    
    return {
        "linhas": len(df),
        "colunas": len(df.columns),
        "nomes_colunas": list(df.columns),
        "memoria_mb": round(memoria_mb, 2),
        "path": path,
        "sucesso": True,
    }

def executar_mostrar_colunas(df: pd.DataFrame, path: str) -> Dict[str, Any]:
    """
    Lista colunas e seus tipos de dados.
    
    Args:
        df: DataFrame a analisar
        path: Caminho do arquivo
    
    Returns:
        Dict com colunas e tipos
    """
    logger.info(f"Colunas presentes: {len(df.columns)}")
    
    return {
        "colunas": list(df.columns),
        "total_colunas": len(df.columns),
        "linhas": len(df),
        "tipos": df.dtypes.astype(str).to_dict(),
        "path": path,
        "sucesso": True,
    }

def executar_preview(df: pd.DataFrame, path: str) -> Dict[str, Any]:
    """
    Mostra primeiras 5 linhas de um arquivo.
    
    Args:
        df: DataFrame a ser analisado
        path: Caminho do arquivo
    
    Returns:
        Dict com preview dos dados
    """
    preview_data = df.head().to_dict("records")
    
    logger.info(f"Preview gerado com {len(preview_data)} linhas")
    logger.info(f"PRIMEIRAS LINHAS:")
    for i, row in enumerate(preview_data, 1):
        logger.info(f"   Linha {i}: {row}")
    
    return {
        "primeiras_5_linhas": preview_data,
        "colunas": list(df.columns),
        "total_linhas": len(df),
        "total_colunas": len(df.columns),
        "path": path,
        "sucesso": True,
    }

def executar_estatistica(
    df: pd.DataFrame,
    operation: str,
    path: str
) -> Dict[str, Any]:
    """
    Executa operações estatísticas: media, soma, max, min.
    
    Args:
        df: DataFrame a analisar
        operation: Tipo de operação ("media", "soma", "max", "min")
        path: Caminho do arquivo
    
    Returns:
        Dict com resultado da estatística
    """
    num_columns = df.select_dtypes(include=["number"])
    
    logger.info(f"Operação: {operation}")
    logger.info(f"Colunas numéricas: {list(num_columns.columns)}")
    
    if num_columns.empty:
        return {
            "erro": "Nenhuma coluna numérica encontrada",
            "sucesso": False,
        }
    
    if operation == "media":
        res = num_columns.mean().to_dict()
        operacao_nome = "Média"
    elif operation == "soma":
        res = num_columns.sum().to_dict()
        operacao_nome = "Soma"
    elif operation == "max":
        res = num_columns.max().to_dict()
        operacao_nome = "Máximo"
    else:  # min
        res = num_columns.min().to_dict()
        operacao_nome = "Mínimo"

    logger.info(f"{operacao_nome}: {res}")
    
    return {
        "resultado": res,
        "colunas_analisadas": list(num_columns.columns),
        "path": path,
        "sucesso": True,
    }

def executar_valores_unicos(
    df: pd.DataFrame,
    coluna: str,
    path: str,
    limite: int = 15,
    offset: int = 0    
) -> Dict[str, Any]:
    """
    Retorna valores únicos de uma coluna com paginação.
    O usuário pergunta sobre valores únicos de uma coluna e o agente deve verificar se a coluna existe e retornar os valores únicos paginados.
    
    Args:
        df: DataFrame a analisar
        coluna: Nome da coluna para extrair valores únicos
        path: Caminho do arquivo
        limite: Quantos valores retornar por vez (padrão: 15)
        offset: Posição de início (padrão: 0)
    
    Returns:
        Dict com valores únicos paginados e contagem total
    """
    try:
        limite = int(limite)
        offset = int(offset)
    except (ValueError, TypeError):
        return {
            "erro": f"Parâmetros inválidos: limite={limite}, offset={offset}",
            "instrucoes": "limite e offset devem ser números inteiros",
            "sucesso": False,
        }
    
    if coluna not in df.columns:
        return {
            "erro": f"Coluna '{coluna}' não encontrada",
            "colunas_disponiveis": list(df.columns),
            "sucesso": False,
        }
    
    try:
        valores_unicos_completo = df[coluna].dropna().unique().tolist()
        quantidade_total = len(valores_unicos_completo)
        
        valores_pagina = valores_unicos_completo[offset:offset + limite]
        has_more = (offset + limite) < quantidade_total
        
        logger.info(f"Valores únicos em '{coluna}': {quantidade_total} total")
        logger.info(f"Página: {offset}-{offset + len(valores_pagina)} de {quantidade_total}")
        
        return {
            "coluna": coluna,
            "valores": valores_pagina,
            "quantidade_retornada": len(valores_pagina),
            "quantidade_total": quantidade_total,
            "offset": offset,
            "limite": limite,
            "tem_proxima_pagina": has_more,
            "pagina_atual": (offset // limite) + 1,
            "total_paginas": (quantidade_total + limite - 1) // limite,
            "nulos": int(df[coluna].isna().sum()),
            "path": path,
            "sucesso": True,
        }
    
    except Exception as e:
        logger.error(f"Erro ao processar coluna '{coluna}': {str(e)}")
        return {
            "erro": f"Erro ao processar: {str(e)}",
            "coluna": coluna,
            "sucesso": False,
        }