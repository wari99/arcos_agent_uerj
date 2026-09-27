import pandas as pd
import traceback
import logging
from typing import Dict, Any
import numpy as np

from tools.commons.settings import FAIXAS_HORARIAS

logger = logging.getLogger(__name__)

def _calcular_faixa_horaria_vetorizado(df: pd.DataFrame, data_coluna: str) -> np.ndarray:
    """
    Calcula faixas horárias de forma vetorizada (muito mais rápido que apply).
    
    Args:
        df: DataFrame com coluna de datetime
        data_coluna: Nome da coluna com datetime
    
    Returns:
        Array numpy com índices de faixas horárias
    """
    horas = df[data_coluna].dt.hour
    minutos = df[data_coluna].dt.minute
    minutos_totais = horas * 60 + minutos
    
    faixas = np.zeros(len(df), dtype=int)
    faixas[(minutos_totais == 0)] = 3
    faixas[(minutos_totais >= 1) & (minutos_totais <= 360)] = 0
    faixas[(minutos_totais >= 361) & (minutos_totais <= 720)] = 1
    faixas[(minutos_totais >= 721) & (minutos_totais <= 1080)] = 2
    faixas[(minutos_totais > 1080)] = 3
    
    return faixas


def executar_filtrar_por_turno(
    df: pd.DataFrame,
    turno: str,
    data_coluna: str,
    path: str,
    filter_column: str = None,
    filter_value: str = None,    
) -> Dict[str, Any]:
    """
    Filtra transações por turno específico (ou todos) com filtro opcional.
    """
    
    logger.info(f"FILTRAR_POR_TURNO: turno={turno}, filtro={filter_column}={filter_value}, data_coluna={data_coluna}")
    
    try:
        if data_coluna not in df.columns:
            logger.error(f"Coluna de data '{data_coluna}' não encontrada")
            return {
                "erro": f"Coluna de data '{data_coluna}' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False,
            }
        
        if df[data_coluna].dtype != 'datetime64[ns]':
            df = df.copy()  
            df[data_coluna] = pd.to_datetime(df[data_coluna], errors='coerce')
            logger.info("Coluna de data convertida para datetime")
        else:
            logger.info("Coluna de data já está em datetime")
        
        faixas_horarias = _calcular_faixa_horaria_vetorizado(df, data_coluna)
        logger.info("Faixas horárias calculadas")
        
        mask = np.ones(len(df), dtype=bool)
        
        if turno != "todos":
            try:
                turno_num = int(turno)
                if turno_num not in FAIXAS_HORARIAS:
                    logger.error(f"Turno '{turno}' inválido")
                    return {
                        "erro": f"Turno '{turno}' inválido. Use 0=Madrugada, 1=Manhã, 2=Tarde, 3=Noite",
                        "sucesso": False,
                    }
                mask &= (faixas_horarias == turno_num)
                info_turno = FAIXAS_HORARIAS[turno_num]
                logger.info(f"Filtrado para turno {turno_num} ({info_turno['nome']})")
            except ValueError:
                logger.error("Turno deve ser um número (0-3) ou 'todos'")
                return {
                    "erro": f"Turno deve ser um número (0-3) ou 'todos'",
                    "sucesso": False,
                }
        else:
            turno_num = None
            logger.info("Usando todos os turnos")
        
        if filter_column is not None and filter_value is not None:
            if filter_column not in df.columns:
                logger.error(f"Coluna de filtro '{filter_column}' não encontrada")
                return {
                    "erro": f"Coluna de filtro '{filter_column}' não encontrada",
                    "colunas_disponiveis": list(df.columns),
                    "sucesso": False,
                }
            
            filter_value_str = str(filter_value)
            mask &= df[filter_column].astype(str).str.contains(
                filter_value_str, 
                case=False, 
                na=False,
                regex=False
            )
            logger.info(f"Filtrado por {filter_column}='{filter_value}'")
        
        df_filtrado = df[mask]
        total_linhas = len(df_filtrado)
        logger.info(f"RESULTADO: {total_linhas} transações encontradas")
        
        if turno != "todos":
            info_turno = FAIXAS_HORARIAS[turno_num]
            return {
                "turno": turno_num,
                "turno_nome": info_turno["nome"],
                "intervalo": info_turno["intervalo"],
                "filter_column": filter_column,
                "filter_value": filter_value,
                "total_transacoes": int(total_linhas),
                "descricao": f"{total_linhas} transações no turno {info_turno['nome']} ({info_turno['intervalo']})",
                "path": path,
                "sucesso": True,
            }
        else:
            distribuicao = {FAIXAS_HORARIAS[t]['nome']: 0 for t in range(4)}
            unique, counts = np.unique(faixas_horarias[mask], return_counts=True)
            for t, count in zip(unique, counts):
                distribuicao[FAIXAS_HORARIAS[t]['nome']] = int(count)
            
            return {
                "turno": "todos",
                "distribuicao_por_turno": distribuicao,
                "total_transacoes": int(total_linhas),
                "path": path,
                "sucesso": True,
            }
    
    except Exception as e:
        error_msg = f"Erro ao filtrar por turno: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            "erro": error_msg,
            "traceback": traceback.format_exc(),
            "sucesso": False,
        }