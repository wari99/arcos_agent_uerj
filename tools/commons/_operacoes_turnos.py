"""
Operações relacionadas a análise por turnos (faixas horárias). As operações são do escopo de analisar_dados_arquivo.py

- filtrar_por_turno: filtra transações por turno específico
- contar_por_turno: conta qual turno teve mais uso
- comparar_por_turno: agregação para gráficos
"""

import pandas as pd
import traceback
from typing import Dict, Any

from tools.commons.settings import FAIXAS_HORARIAS


def _determinar_faixa_horaria(hora: int, minuto: int = 0) -> int:
    """
    Determina qual faixa horária (turno) uma hora e minuto obtida em datetime pertencem.
    
    Faixas definidas (em minutos desde meia-noite):
    - 0 = Madrugada: 00:01 até 06:00 (minutos 1 até 360)
    - 1 = Manhã:     06:01 até 12:00 (minutos 361 até 720)
    - 2 = Tarde:     12:01 até 18:00 (minutos 721 até 1080)
    - 3 = Noite:     18:01 até 23:59 (minutos 1081 até 1439) + 00:00 (minuto 0)
    
    Args:
        hora: Hora do dia (0-23)
        minuto: Minuto da hora (0-59), padrão=0
    
    Returns:
        int: Índice da faixa (0=madrugada, 1=manhã, 2=tarde, 3=noite)
    """
    minutos_totais = hora * 60 + minuto
    
    if minutos_totais == 0:
        return 3  
    elif 1 <= minutos_totais <= 360:
        return 0
    elif 361 <= minutos_totais <= 720:
        return 1
    elif 721 <= minutos_totais <= 1080:
        return 2
    else:
        return 3


def executar_filtrar_por_turno(
    df: pd.DataFrame,
    turno: str,
    data_coluna: str,
    arquivo_local: str,
    filter_column: str = "None",
    filter_value: str = "None",    
) -> Dict[str, Any]:
    """
    Filtra transações por turno específico (ou todos) com filtro opcional.
    
    Args:
        df: DataFrame a analisar
        turno: "0", "1", "2", "3" ou "todos"
        filter_column: Coluna adicional para filtrar (opcional)
        filter_value: Valor a buscar naquela coluna (opcional)
        data_coluna: Nome da coluna com datetime
        arquivo_local: Caminho do arquivo
    
    Returns:
        Dict com resultado da filtragem
    """
    
    print(f"\n FILTRAR_POR_TURNO:")
    print(f"   Turno: {turno}")
    print(f"   Coluna de filtro: {filter_column}")
    print(f"   Valor de filtro: {filter_value}")
    print(f"   Coluna de data: {data_coluna}")
    
    try:
        if data_coluna not in df.columns:
            return {
                "erro": f"Coluna de data '{data_coluna}' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False,
            }
        
        df[data_coluna] = pd.to_datetime(df[data_coluna], errors='coerce')
        print(f"✅ Coluna de data convertida para datetime")
        
        df['_hora_extraida'] = df[data_coluna].dt.hour
        
        df['_minuto_extraido'] = df[data_coluna].dt.minute
        df['_faixa_horaria'] = df.apply(lambda row: _determinar_faixa_horaria(row['_hora_extraida'], row['_minuto_extraido']), axis=1)        
        print(f"✅ Faixas horárias calculadas")
        
        if turno != "todos":
            try:
                turno_num = int(turno)
                if turno_num not in FAIXAS_HORARIAS:
                    return {
                        "erro": f"Turno '{turno}' inválido. Use 0=Manhã, 1=Tarde, 2=Noite, 3=Madrugada",
                        "sucesso": False,
                    }
                df_filtrado = df[df['_faixa_horaria'] == turno_num]
                info_turno = FAIXAS_HORARIAS[turno_num]
                print(f"✅ Filtrado para turno {turno_num} ({info_turno['nome']})")
            except ValueError:
                return {
                    "erro": f"Turno deve ser um número (0-3) ou 'todos'",
                    "sucesso": False,
                }
        else:
            df_filtrado = df.copy()
            print(f"✅ Usando todos os turnos")
        
        if filter_column and filter_value is not None: # filtro adicional se fornecer coluna
            if filter_column not in df_filtrado.columns:
                return {
                    "erro": f"Coluna de filtro '{filter_column}' não encontrada",
                    "colunas_disponiveis": list(df_filtrado.columns),
                    "sucesso": False,
                }
            
            df_filtrado = df_filtrado[
                df_filtrado[filter_column].astype(str).str.contains(str(filter_value), case=False, na=False)
            ]
            print(f"✅ Filtrado por {filter_column}='{filter_value}'")
        
        total_linhas = len(df_filtrado)
        print(f"\n    RESULTADO: {total_linhas} transações encontradas")
        
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
                "arquivo_local": arquivo_local,
                "sucesso": True,
            }
        else:
            distribuicao = {}
            for t in range(4):
                count = len(df_filtrado[df_filtrado['_faixa_horaria'] == t])
                if count > 0:
                    distribuicao[FAIXAS_HORARIAS[t]['nome']] = int(count)
            
            return {
                "turno": "todos",
                "distribuicao_por_turno": distribuicao,
                "total_transacoes": int(total_linhas),
                "arquivo_local": arquivo_local,
                "sucesso": True,
            }
    
    except Exception as e:
        error_msg = f"Erro ao filtrar por turno: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "erro": error_msg,
            "traceback": traceback.format_exc(),
            "sucesso": False,
        }