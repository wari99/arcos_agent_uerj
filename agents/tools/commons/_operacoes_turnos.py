"""
Operações por TURNO (faixa horária do dia). As operações são do escopo de analisar_dados_arquivo.py

Turnos (definidos em FAIXAS_HORARIAS): 0 = Madrugada, 1 = Manhã, 2 = Tarde, 3 = Noite.

Operações:
- executar_filtrar_por_turno: total de transações de um turno (ou a distribuição de todos os turnos)
- executar_contar_por_turno: distribuição por turno com porcentagens e o turno de maior uso
- executar_comparar_por_turno: distribuição por turno em lista, boa para gráficos

As três seguem o mesmo caminho (repetido de propósito em cada função, para ler cada uma de cima a baixo;
só o cálculo do turno fica em calcular_faixas_horarias):
  1. descobrir o turno de cada linha a partir da coluna de data/hora;
  2. aplicar o filtro opcional "coluna contém valor";
  3. contar quantas linhas caem em cada turno.
"""

import logging
import traceback
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from agents.tools.commons._apoio_colunas import mascara_por_valor, validar_coluna
from agents.tools.commons.settings import FAIXAS_HORARIAS

logger = logging.getLogger(__name__)


# ============================================================
# FUNÇÃO DE APOIO
# ============================================================

def calcular_faixas_horarias(datas: pd.Series) -> np.ndarray:
    """
    Descobre o turno de cada data/hora, de forma vetorizada (muito mais rápido que linha a linha).

    Args:
        datas: série de datas/horas (tipo datetime)

    Returns:
        Array com o turno de cada linha: 0 = Madrugada, 1 = Manhã, 2 = Tarde, 3 = Noite.
        Linhas com data inválida (NaT) ficam com 0 (Madrugada).
    """
    minutos_totais = datas.dt.hour * 60 + datas.dt.minute

    faixas = np.zeros(len(datas), dtype=int)
    faixas[minutos_totais == 0] = 3                                   # 00:00 exato conta como Noite
    faixas[(minutos_totais >= 1) & (minutos_totais <= 360)] = 0       # 00:01 até 06:00 = Madrugada
    faixas[(minutos_totais >= 361) & (minutos_totais <= 720)] = 1     # 06:01 até 12:00 = Manhã
    faixas[(minutos_totais >= 721) & (minutos_totais <= 1080)] = 2    # 12:01 até 18:00 = Tarde
    faixas[minutos_totais > 1080] = 3                                 # depois das 18:00 = Noite

    return faixas

def executar_filtrar_por_turno( # operacao: filtrar por turno
    df: pd.DataFrame,
    turno: str,
    coluna_data: str,
    path: str,
    coluna: str = None,
    valor: str = None,
    memo: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Filtra transações por turno específico (ou todos) com filtro opcional.

    Args:
        df: DataFrame a analisar
        turno: "0" a "3" (Madrugada, Manhã, Tarde, Noite) ou "todos"
        coluna_data: coluna com a data e hora da transação
        path: Caminho do arquivo
        coluna, valor: filtro opcional (linhas em que a coluna contém o valor)
        memo: dicionário do cache do arquivo, para reaproveitar o cálculo dos turnos
    """

    logger.info(f"FILTRAR_POR_TURNO: turno={turno}, filtro={coluna}={valor}, coluna_data={coluna_data}")

    try:
        coluna_data, erro = validar_coluna(df, coluna_data, "Coluna de data '{}' não encontrada")
        if erro:
            return erro
        if not coluna_data:
            return {
                "erro": "Coluna de data '' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False,
            }

        chave_memo = ("faixas_horarias", coluna_data)
        if memo is not None and chave_memo in memo and len(memo[chave_memo]) == len(df):
            logger.info("Faixas horárias já calculadas (reaproveitadas)")
            faixas_horarias = memo[chave_memo]
        else:
            datas = df[coluna_data]
            if not pd.api.types.is_datetime64_any_dtype(datas):
                # "02/01/2026" é 2 de janeiro (dia/mês/ano) nos arquivos da base. Sem avisar isso, o pandas
                # lê como mês/dia e datas como "31/12/2025" 
                primeiro_valor = datas.dropna().astype(str).head(1)
                dia_primeiro = len(primeiro_valor) > 0 and "/" in primeiro_valor.iloc[0]
                datas = pd.to_datetime(datas, errors="coerce", dayfirst=dia_primeiro)

            quantidade_invalidas = int(datas.isna().sum())
            if quantidade_invalidas > 0:
                logger.warning(f"{quantidade_invalidas} data(s) inválida(s) em '{coluna_data}': contadas como Madrugada")

            faixas_horarias = calcular_faixas_horarias(datas)
            logger.info("Faixas horárias calculadas")

            if memo is not None:
                memo[chave_memo] = faixas_horarias

        mascara = np.ones(len(df), dtype=bool)

        turno_num = None
        if turno != "todos":
            try:
                turno_num = int(turno)
            except ValueError:
                logger.error("Turno deve ser um número (0-3) ou 'todos'")
                return {
                    "erro": "Turno deve ser um número (0-3) ou 'todos'",
                    "sucesso": False,
                }

            if turno_num not in FAIXAS_HORARIAS:
                logger.error(f"Turno '{turno}' inválido")
                return {
                    "erro": f"Turno '{turno}' inválido. Use 0=Madrugada, 1=Manhã, 2=Tarde, 3=Noite",
                    "sucesso": False,
                }

            mascara &= (faixas_horarias == turno_num)
            logger.info(f"Filtrado para turno {turno_num} ({FAIXAS_HORARIAS[turno_num]['nome']})")
        else:
            logger.info("Usando todos os turnos")

        if coluna is not None and valor is not None:
            coluna, erro = validar_coluna(df, coluna, "Coluna de filtro '{}' não encontrada")
            if erro:
                return erro
            linha_casou, _ = mascara_por_valor(df, coluna, valor)
            mascara &= linha_casou.to_numpy()
            logger.info(f"Filtrado por {coluna}='{valor}'")

        total_linhas = int(mascara.sum())
        logger.info(f"RESULTADO: {total_linhas} transações encontradas")

        if turno_num is not None:
            info_turno = FAIXAS_HORARIAS[turno_num]
            return {
                "turno": turno_num,
                "turno_nome": info_turno["nome"],
                "intervalo": info_turno["intervalo"],
                "coluna": coluna,
                "valor": valor,
                "total_transacoes": total_linhas,
                "descricao": f"{total_linhas} transações no turno {info_turno['nome']} ({info_turno['intervalo']})",
                "path": path,
                "sucesso": True,
            }

        distribuicao = {}
        for t in range(4):
            distribuicao[FAIXAS_HORARIAS[t]["nome"]] = 0

        turnos, quantidades = np.unique(faixas_horarias[mascara], return_counts=True)
        for t, quantidade in zip(turnos, quantidades):
            distribuicao[FAIXAS_HORARIAS[int(t)]["nome"]] = int(quantidade)

        return {
            "turno": "todos",
            "distribuicao_por_turno": distribuicao,
            "total_transacoes": total_linhas,
            "path": path,
            "sucesso": True,
        }

    except Exception as e:
        mensagem_erro = f"Erro ao filtrar por turno: {str(e)}"
        logger.error(mensagem_erro)
        logger.error(traceback.format_exc())
        return {"erro": mensagem_erro, "sucesso": False}

def executar_contar_por_turno( # operacao: contar por turno
    df: pd.DataFrame,
    coluna_data: str,
    path: str,
    coluna: str = None,
    valor: str = None,
    memo: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Distribuição das transações por turno, com porcentagens e o turno de maior uso. O filtro (coluna contém valor) é opcional; sem ele, usa todas as linhas.
    """

    logger.info("CONTAR_POR_TURNO")
    logger.info(f"Coluna de filtro: {coluna}")
    logger.info(f"Valor de filtro: {valor}")
    logger.info(f"Coluna de data: {coluna_data}")

    try:
        coluna_data, erro = validar_coluna(df, coluna_data, "Coluna de data '{}' não encontrada")
        if erro:
            return erro
        if not coluna_data:
            return {
                "erro": "Coluna de data '' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False,
            }

        chave_memo = ("faixas_horarias", coluna_data)
        if memo is not None and chave_memo in memo and len(memo[chave_memo]) == len(df):
            logger.info("Faixas horárias já calculadas (reaproveitadas)")
            faixas_horarias = memo[chave_memo]
        else:
            datas = df[coluna_data]
            if not pd.api.types.is_datetime64_any_dtype(datas):
                # Textos com "/" são lidos com o dia primeiro ("02/01/2026" = 2 de janeiro)
                primeiro_valor = datas.dropna().astype(str).head(1)
                dia_primeiro = len(primeiro_valor) > 0 and "/" in primeiro_valor.iloc[0]
                datas = pd.to_datetime(datas, errors="coerce", dayfirst=dia_primeiro)

            quantidade_invalidas = int(datas.isna().sum())
            if quantidade_invalidas > 0:
                logger.warning(f"{quantidade_invalidas} data(s) inválida(s) em '{coluna_data}': contadas como Madrugada")

            faixas_horarias = calcular_faixas_horarias(datas)
            logger.info("Faixas horárias calculadas")

            if memo is not None:
                memo[chave_memo] = faixas_horarias

        mascara = np.ones(len(df), dtype=bool)

        tem_filtro = bool(coluna) and valor is not None
        if tem_filtro:
            coluna, erro = validar_coluna(df, coluna, "Coluna de filtro '{}' não encontrada")
            if erro:
                return erro
            linha_casou, _ = mascara_por_valor(df, coluna, valor)
            mascara &= linha_casou.to_numpy()
            logger.info(f"Filtrado por {coluna}='{valor}'")
        else:
            logger.info("Sem filtro aplicado: usando todas as linhas")

        total_linhas = int(mascara.sum())
        logger.info(f"Total de linhas a analisar: {total_linhas}")

        if total_linhas == 0:
            logger.warning("Nenhuma linha encontrada")
            return {
                "erro": "Nenhuma transação encontrada",
                "sucesso": False,
            }

        turnos, quantidades = np.unique(faixas_horarias[mascara], return_counts=True)

        contagem_por_turno = {}
        turno_com_mais = None
        maior_quantidade = 0

        logger.info("Distribuição por turno:")
        for turno_idx, quantidade in zip(turnos, quantidades):
            turno_idx = int(turno_idx)
            quantidade = int(quantidade)
            info_turno = FAIXAS_HORARIAS[turno_idx]
            porcentagem = round((quantidade / total_linhas) * 100, 2)

            contagem_por_turno[info_turno["nome"]] = {
                "quantidade": quantidade,
                "intervalo": info_turno["intervalo"],
                "porcentagem": porcentagem,
            }

            if quantidade > maior_quantidade:
                maior_quantidade = quantidade
                turno_com_mais = info_turno["nome"]

            logger.info(f"{info_turno['nome']}: {quantidade} ({porcentagem}%)")

        if tem_filtro:
            filtro_descricao = f"Filtro: {coluna}='{valor}'"
        else:
            filtro_descricao = "Sem filtro (todas as transações)"

        porcentagem_do_maior = contagem_por_turno[turno_com_mais]["porcentagem"]

        return {
            "filtro_aplicado": filtro_descricao,
            "coluna": coluna,
            "valor": valor,
            "total_transacoes": total_linhas,
            "contagem_por_turno": contagem_por_turno,
            "turno_com_mais_uso": turno_com_mais,
            "turno_com_mais_uso_quantidade": maior_quantidade,
            "resumo": f"{turno_com_mais} teve o maior uso ({maior_quantidade} transações, {porcentagem_do_maior}%)",
            "path": path,
            "sucesso": True,
        }

    except Exception as e:
        mensagem_erro = f"Erro ao contar por turno: {str(e)}"
        logger.error(mensagem_erro)
        logger.error(traceback.format_exc())
        return {"erro": mensagem_erro, "sucesso": False}

def executar_comparar_por_turno( # operacao: comparar por turno
    df: pd.DataFrame,
    coluna_data: str,
    path: str,
    coluna: str = None,
    valor: str = None,
    memo: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Agregação por turno para gráficos e comparações: quantidade de transações em cada turno. O filtro (coluna contém valor) é opcional.

    Exemplo de resposta:
    {
        "dados_turno": [
            {"Turno": "Manhã", "Quantidade": 64560, "Intervalo": "06:01 até 12:00", "Porcentagem": 68.8},
            {"Turno": "Tarde", "Quantidade": 29223, "Intervalo": "12:01 até 18:00", "Porcentagem": 31.2},
        ],
        "sucesso": True
    }
    """

    logger.info("COMPARAR_POR_TURNO")
    logger.info(f"Filtro: {coluna}='{valor}' (opcional)")

    try:
        coluna_data, erro = validar_coluna(df, coluna_data, "Coluna de data '{}' não encontrada")
        if erro:
            return erro
        if not coluna_data:
            return {
                "erro": "Coluna de data '' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False,
            }

        chave_memo = ("faixas_horarias", coluna_data)
        if memo is not None and chave_memo in memo and len(memo[chave_memo]) == len(df):
            logger.info("Faixas horárias já calculadas (reaproveitadas)")
            faixas_horarias = memo[chave_memo]
        else:
            datas = df[coluna_data]
            if not pd.api.types.is_datetime64_any_dtype(datas):
                # Textos com "/" são lidos com o dia primeiro ("02/01/2026" = 2 de janeiro)
                primeiro_valor = datas.dropna().astype(str).head(1)
                dia_primeiro = len(primeiro_valor) > 0 and "/" in primeiro_valor.iloc[0]
                datas = pd.to_datetime(datas, errors="coerce", dayfirst=dia_primeiro)

            quantidade_invalidas = int(datas.isna().sum())
            if quantidade_invalidas > 0:
                logger.warning(f"{quantidade_invalidas} data(s) inválida(s) em '{coluna_data}': contadas como Madrugada")

            faixas_horarias = calcular_faixas_horarias(datas)
            logger.info("Faixas horárias calculadas")

            if memo is not None:
                memo[chave_memo] = faixas_horarias

        mascara = np.ones(len(df), dtype=bool)

        if coluna and valor:
            coluna, erro = validar_coluna(df, coluna, "Coluna de filtro '{}' não encontrada")
            if erro:
                return erro
            linha_casou, _ = mascara_por_valor(df, coluna, valor)
            mascara &= linha_casou.to_numpy()
            logger.info(f"Filtrado por {coluna}='{valor}'")

            total_com_filtro = int(mascara.sum())
            logger.info(f"Filtrado: {total_com_filtro} linhas com '{valor}'")

            if total_com_filtro == 0:
                logger.warning("Nenhuma linha encontrada para filtro")
                return {
                    "erro": f"Nenhuma transação encontrada para filtro {coluna}='{valor}'",
                    "sucesso": False,
                }

        total_linhas = int(mascara.sum())

        turnos, quantidades = np.unique(faixas_horarias[mascara], return_counts=True)

        dados_turno = []
        for turno_idx, quantidade in zip(turnos, quantidades):
            turno_idx = int(turno_idx)
            quantidade = int(quantidade)
            info_turno = FAIXAS_HORARIAS[turno_idx]
            porcentagem = round((quantidade / total_linhas) * 100, 2)

            dados_turno.append({
                "Turno": info_turno["nome"],
                "Quantidade": quantidade,
                "Intervalo": info_turno["intervalo"],
                "Porcentagem": porcentagem,
            })
            logger.info(f"{info_turno['nome']}: {quantidade} ({porcentagem}%)")

        if not dados_turno:
            logger.warning("Sem dados para comparar")
            return {
                "erro": "Nenhuma transação encontrada",
                "sucesso": False,
            }

        logger.info(f"Comparação por turno gerada: {total_linhas} transações em {len(dados_turno)} turno(s)")

        return {
            "coluna": coluna,
            "valor": valor,
            "total_transacoes": total_linhas,
            "dados_turno": dados_turno,
            "path": path,
            "sucesso": True,
        }

    except Exception as e:
        mensagem_erro = f"Erro ao comparar por turno: {str(e)}"
        logger.error(mensagem_erro)
        logger.error(traceback.format_exc())
        return {"erro": mensagem_erro, "sucesso": False}
