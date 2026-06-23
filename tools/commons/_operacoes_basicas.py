"""
Operações básicas de análise de dados. As operações são do escopo de analisar_dados_arquivo.py

- contar_linhas
- mostrar_colunas
- preview
- media, soma, max, min
"""

import pandas as pd
from typing import Dict, Any


def executar_contar_linhas(df: pd.DataFrame, arquivo_local: str) -> Dict[str, Any]:
    """
    Conta total de linhas no arquivo.
    
    Args:
        df: DataFrame a analisar
        arquivo_local: Caminho do arquivo
    
    Returns:
        Dict com resultado da contagem
    """
    memoria_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    
    print(f"✅ Contagem: {len(df)} linhas")
    
    return {
        "linhas": len(df),
        "colunas": len(df.columns),
        "nomes_colunas": list(df.columns),
        "memoria_mb": round(memoria_mb, 2),
        "arquivo_local": arquivo_local,
        "sucesso": True,
    }


def executar_mostrar_colunas(df: pd.DataFrame, arquivo_local: str) -> Dict[str, Any]:
    """
    Lista colunas e seus tipos de dados.
    
    Args:
        df: DataFrame a analisar
        arquivo_local: Caminho do arquivo
    
    Returns:
        Dict com colunas e tipos
    """
    print(f"✅ Colunas listadas: {len(df.columns)}")
    
    return {
        "colunas": list(df.columns),
        "total_colunas": len(df.columns),
        "linhas": len(df),
        "tipos": df.dtypes.astype(str).to_dict(),
        "arquivo_local": arquivo_local,
        "sucesso": True,
    }


def executar_preview(df: pd.DataFrame, arquivo_local: str) -> Dict[str, Any]:
    """
    Mostra primeiras 5 linhas do arquivo.
    
    Args:
        df: DataFrame a analisar
        arquivo_local: Caminho do arquivo
    
    Returns:
        Dict com preview dos dados
    """
    preview_data = df.head().to_dict("records")
    
    print(f"✅ Preview gerado com {len(preview_data)} linhas")
    print(f"\n📄 PRIMEIRAS LINHAS:")
    for i, row in enumerate(preview_data, 1):
        print(f"   Linha {i}: {row}")
    
    return {
        "primeiras_5_linhas": preview_data,
        "colunas": list(df.columns),
        "total_linhas": len(df),
        "total_colunas": len(df.columns),
        "arquivo_local": arquivo_local,
        "sucesso": True,
    }


def executar_estatistica(
    df: pd.DataFrame,
    operation: str,
    arquivo_local: str
) -> Dict[str, Any]:
    """
    Executa operações estatísticas: media, soma, max, min.
    
    Args:
        df: DataFrame a analisar
        operation: Tipo de operação ("media", "soma", "max", "min")
        arquivo_local: Caminho do arquivo
    
    Returns:
        Dict com resultado da estatística
    """
    numericas = df.select_dtypes(include=["number"])
    
    print(f"\n📊 Operação: {operation}")
    print(f"   Colunas numéricas: {list(numericas.columns)}")
    
    if numericas.empty:
        return {
            "erro": "Nenhuma coluna numérica encontrada",
            "sucesso": False,
        }
    
    if operation == "media":
        res = numericas.mean().to_dict()
        operacao_nome = "Média"
    elif operation == "soma":
        res = numericas.sum().to_dict()
        operacao_nome = "Soma"
    elif operation == "max":
        res = numericas.max().to_dict()
        operacao_nome = "Máximo"
    else:  # min
        res = numericas.min().to_dict()
        operacao_nome = "Mínimo"

    print(f"✅ {operacao_nome}: {res}")
    
    return {
        "resultado": res,
        "colunas_analisadas": list(numericas.columns),
        "arquivo_local": arquivo_local,
        "sucesso": True,
    }