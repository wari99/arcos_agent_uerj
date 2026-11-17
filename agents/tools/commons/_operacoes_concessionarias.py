"""
Operações específicas para tarifas de concessionárias (MetrôRio, SuperVia, Barcas).
- leitura_tarifa: Consulta tarifas históricas.

As planilhas de tarifa têm títulos antes do cabeçalho e cada concessionária usa nomes diferentes.
Por isso o modelo pode (e deve) dizer ao código quais são as colunas e onde está o cabeçalho,
olhando as linhas reais com 'preview': coluna_tarifa, coluna_data, coluna_descricao e linha_cabecalho.
O que ele não informar o código ainda tenta inferir (palavras-chave nos nomes e nos dados),
e o resultado avisa quando houve inferência.
"""

import logging
from collections.abc import Callable
from typing import Any, NamedTuple

import pandas as pd

from agents.tools.commons._apoio_colunas import validar_coluna

logger = logging.getLogger(__name__)

PALAVRAS_TARIFA = ["tarifa autorizada", "tarifa", "valor", "preço"]
PALAVRAS_DATA = ["vigência", "vigeancia", "inicio", "data", "início"]
PALAVRAS_DESCRICAO = ["descrição", "descricao", "decreto", "deliberação", "deliberacao"]

PALAVRAS_SOCIAL = ("social",)
PALAVRAS_NORMAL = ("inteira", "normal", "autorizada")

# Normal primeiro, depois Social, depois outros
ORDEM_TIPOS = {"Normal": 0, "Social": 1, "Outros": 2}


class _Colunas(NamedTuple):
    tarifa: str
    data: str
    descricao: str | None


def _classificar_tipo_tarifa(descricao: str) -> str:
    """
    Classifica o tipo de tarifa baseado na descrição.

    Args:
        descricao: Descrição da tarifa

    Returns:
        "Normal", "Social", ou "Outros"
    """
    desc_lower = str(descricao).lower()

    if any(p in desc_lower for p in PALAVRAS_SOCIAL):
        return "Social"
    if any(p in desc_lower for p in PALAVRAS_NORMAL):
        return "Normal"
    return "Outros"


def _detectar_coluna_por_conteudo(df: pd.DataFrame, palavras_chave: list) -> int | None:
    """
    Detecta coluna procurando por palavras-chave nos nomes das colunas
    e, se não achar, nos dados (primeiras 5 linhas).

    Args:
        df: DataFrame a analisar
        palavras_chave: Lista de palavras para procurar (ex: ["vigência", "vigeancia", "data"])

    Returns:
        Índice da coluna encontrada ou None
    """
    palavras = [p.lower() for p in palavras_chave]

    for idx, col_name in enumerate(df.columns):
        nome = str(col_name).lower()
        if any(p in nome for p in palavras):
            return idx

    for linha in range(min(5, len(df))):
        for col_idx in range(len(df.columns)):
            valor = str(df.iloc[linha, col_idx]).lower()
            if len(valor) > 3 and any(p in valor for p in palavras):
                return col_idx

    return None


def _usar_linha_como_cabecalho(df: pd.DataFrame, posicao: int) -> pd.DataFrame:
    """
    Usa a linha na posição `posicao` (0 = primeira linha) como nomes das colunas
    e descarta essa linha e todas as anteriores (títulos da planilha).
    Células vazias na linha viram "Col_<número>".
    """
    nomes = [str(valor).strip() for valor in df.iloc[posicao]]

    novos_nomes = []
    for indice, nome in enumerate(nomes):
        if nome and nome != "nan":
            novos_nomes.append(nome)
        else:
            novos_nomes.append(f"Col_{indice}")

    df.columns = novos_nomes
    return df.iloc[posicao + 1 :].reset_index(drop=True)


def _limpar_e_renomear_colunas(
    df: pd.DataFrame, linha_cabecalho: int | None = None
) -> pd.DataFrame:
    """
    Limpa e renomeia colunas.

    Faz:
    - Remove colunas totalmente vazias
    - Define o cabeçalho: usa a linha informada (linha_cabecalho) ou, sem ela, tenta adivinhar
      (primeira linha com muito texto)
    - Renomeia "Unnamed: X" baseado em conteúdo

    Args:
        df: DataFrame com potenciais problemas estruturais
        linha_cabecalho: posição da linha com os nomes reais das colunas (None = tentar adivinhar)

    Returns:
        DataFrame limpo e com colunas renomeadas
    """
    logger.debug(f"Limpando colunas (antes: {len(df.columns)})")

    df = df.dropna(axis=1, how="all")
    logger.debug(f"Colunas vazias removidas: {len(df.columns)} restantes")

    if linha_cabecalho is not None:
        # O modelo informou onde está o cabeçalho: não há o que adivinhar
        logger.debug(f"Linha {linha_cabecalho} usada como cabeçalho (informada)")
        df = _usar_linha_como_cabecalho(df, linha_cabecalho)
    elif len(df) > 0:
        # Sem informação: primeira linha com muito texto (> 20 caracteres em média) pode ser um cabeçalho adicional
        primeira_linha = df.iloc[0]
        media_tamanho = primeira_linha.astype(str).apply(len).mean()

        if media_tamanho > 20:
            logger.debug(
                f"Primeira linha usada como cabeçalho (média: {media_tamanho:.0f} chars): {primeira_linha.values[:3]}"
            )
            df = _usar_linha_como_cabecalho(df, 0)

    # "Unnamed": tenta deduzir o nome pelo conteúdo
    novos_nomes = []
    for idx, col in enumerate(df.columns):
        col_str = str(col)
        if "unnamed" not in col_str.lower():
            novos_nomes.append(col_str)
            continue
        amostra = df.iloc[:5, idx].dropna().unique()
        novos_nomes.append(
            f"Col_{idx}_{str(amostra[0])[:30]}" if len(amostra) > 0 else f"Col_{idx}"
        )

    df.columns = novos_nomes
    logger.debug(f"Colunas renomeadas: {novos_nomes}")

    return df


def _registro(
    linha: dict, cols: _Colunas, descricao_padrao: str, com_ano: bool = False
) -> dict:
    """Converte uma linha em registro de tarifa. `descricao_padrao` é usado se não houver coluna de descrição."""
    data = linha[cols.data]
    descricao = (
        str(linha[cols.descricao]).strip()
        if cols.descricao and cols.descricao in linha
        else descricao_padrao
    )
    tarifa = {
        "tipo": _classificar_tipo_tarifa(descricao),
        "tarifa": round(float(linha[cols.tarifa]), 2),
    }
    datas = {
        "data_vigencia": data.strftime("%d/%m/%Y"),
        "data_vigencia_iso": data.strftime("%Y-%m-%d"),
    }

    if com_ano:
        return {**tarifa, **datas, "ano": int(data.year), "descricao": descricao}
    return {**tarifa, "descricao": descricao, **datas}


def _tarifas_vigentes(registros: pd.DataFrame, cols: _Colunas):
    """Todas as tarifas da data mais recente de `registros`. Retorna (tarifas, data)."""
    data = registros[cols.data].max()
    vigentes = registros[registros[cols.data] == data].to_dict("records")
    tarifas = [_registro(r, cols, "Normal") for r in vigentes]
    tarifas.sort(key=lambda t: ORDEM_TIPOS.get(t["tipo"], 3))
    return tarifas, data


# ============================================================
# CONSULTAS (cada uma recebe df já limpo, ordenado por data desc e com a coluna '_ano')
# ============================================================


def _consulta_atual(
    df: pd.DataFrame, cols: _Colunas, ano: int | None, path: str
) -> dict[str, Any]:
    tarifas, data = _tarifas_vigentes(df, cols)
    logger.debug(f"{len(tarifas)} tipo(s) de tarifa na data mais recente")
    return {
        "consulta_tipo": "atual",
        "tarifas": tarifas,
        "data_vigencia": data.strftime("%d/%m/%Y"),
        "path": path,
        "sucesso": True,
    }


def _consulta_ano(
    df: pd.DataFrame, cols: _Colunas, ano: int | None, path: str
) -> dict[str, Any]:
    if not ano:
        return {"erro": "Parâmetro 'ano' é obrigatório", "sucesso": False}

    registros_ano = df[df["_ano"] == int(ano)]
    if registros_ano.empty:
        return {
            "erro": f"Nenhuma tarifa encontrada para {int(ano)}",
            "anos_disponiveis": [int(a) for a in sorted(df["_ano"].unique())],
            "sucesso": False,
        }

    tarifas, data = _tarifas_vigentes(registros_ano, cols)
    logger.debug(f"{len(tarifas)} tipo(s) de tarifa vigente em {int(ano)}")
    return {
        "consulta_tipo": "ano",
        "ano": int(ano),
        "tarifas": tarifas,
        "data_vigencia": data.strftime("%d/%m/%Y"),
        "path": path,
        "sucesso": True,
    }


def _consulta_ultima_mudanca(
    df: pd.DataFrame, cols: _Colunas, ano: int | None, path: str
) -> dict[str, Any]:
    linha = df.iloc[0].to_dict()
    registro = _registro(linha, cols, "N/A")
    dias_desde = (pd.Timestamp.now() - linha[cols.data]).days

    return {
        "consulta_tipo": "ultima_mudanca",
        "tipo": registro["tipo"],
        "tarifa": registro["tarifa"],
        "data_mudanca": registro["data_vigencia"],
        "data_mudanca_iso": registro["data_vigencia_iso"],
        "dias_desde_mudanca": int(dias_desde),
        "descricao": registro["descricao"],
        "path": path,
        "sucesso": True,
    }


def _consulta_historico(
    df: pd.DataFrame, cols: _Colunas, ano: int | None, path: str
) -> dict[str, Any]:
    historico = [_registro(r, cols, "N/A", com_ano=True) for r in df.to_dict("records")]
    valores = [h["tarifa"] for h in historico]
    logger.debug(
        f"{len(historico)} registros (menor: {min(valores):.2f}, maior: {max(valores):.2f})"
    )

    return {
        "consulta_tipo": "historico",
        "total_registros": len(historico),
        "historico": historico,
        "menor_tarifa": min(valores),
        "maior_tarifa": max(valores),
        "path": path,
        "sucesso": True,
    }


def _consulta_buscar_por_valor(
    df: pd.DataFrame, cols: _Colunas, ano: int | None, path: str
) -> dict[str, Any]:
    valor_max = ano  # Reutiliza parâmetro 'ano' como valor máximo
    if valor_max is None:
        return {
            "erro": "Parâmetro 'ano' é usado como valor_max para buscar_por_valor",
            "sucesso": False,
        }

    valor_max = float(valor_max)
    # reordena de propósito: o sort não é estável e o desempate entre datas iguais faz parte da saída atual
    resultados = df[df[cols.tarifa] <= valor_max].sort_values(
        by=cols.data, ascending=False
    )

    if resultados.empty:
        return {
            "consulta_tipo": "buscar_por_valor",
            "valor_max": valor_max,
            "mensagem": f"Nenhuma tarifa encontrada abaixo de R$ {valor_max:.2f}",
            "menor_tarifa_historica": round(float(df[cols.tarifa].min()), 2),
            "sucesso": True,
        }

    encontrados = [
        _registro(r, cols, "N/A", com_ano=True) for r in resultados.to_dict("records")
    ]
    logger.debug(f"{len(encontrados)} registros <= R$ {valor_max:.2f}")

    return {
        "consulta_tipo": "buscar_por_valor",
        "valor_max": valor_max,
        "total_encontrados": len(encontrados),
        "resultados": encontrados,
        "path": path,
        "sucesso": True,
    }


_CONSULTAS: dict[str, Callable[..., dict[str, Any]]] = {
    "atual": _consulta_atual,
    "ano": _consulta_ano,
    "ultima_mudanca": _consulta_ultima_mudanca,
    "historico": _consulta_historico,
    "buscar_por_valor": _consulta_buscar_por_valor,
}


def _definir_colunas(
    df: pd.DataFrame,
    coluna_tarifa: str | None,
    coluna_data: str | None,
    coluna_descricao: str | None,
) -> tuple[_Colunas | None, list[str], dict[str, Any] | None]:
    """
    Define quais colunas são a tarifa, a data de vigência e a descrição.

    Para cada uma:
      - se o modelo informou o nome, confere se existe (corrigindo erros leves de digitação);
      - se não informou, tenta inferir por palavras-chave nos nomes e nos dados.

    Devolve três valores: (colunas, lista do que foi inferido, erro).
    Se houver erro, o primeiro valor é None.
    """
    candidatas = (
        ("tarifa", coluna_tarifa, PALAVRAS_TARIFA),
        ("data", coluna_data, PALAVRAS_DATA),
        ("descricao", coluna_descricao, PALAVRAS_DESCRICAO),
    )

    nomes: dict[str, str | None] = {}
    indices_testados: dict[str, int | None] = {
        "tarifa": None,
        "data": None,
        "descricao": None,
    }
    inferidas: list[str] = []

    for rotulo, informada, palavras in candidatas:
        if informada:
            nome, erro = validar_coluna(
                df, informada, f"Coluna de {rotulo} '{{}}' não encontrada"
            )
            if erro:
                return None, [], erro
            nomes[rotulo] = nome
            continue

        indice = _detectar_coluna_por_conteudo(df, palavras)
        indices_testados[rotulo] = indice
        if indice is None:
            nomes[rotulo] = None
        else:
            nomes[rotulo] = df.columns[indice]
            inferidas.append(rotulo)

    if nomes["tarifa"] is None:
        logger.error(
            f"Coluna de TARIFA não encontrada (palavras: {PALAVRAS_TARIFA}). Colunas: {list(df.columns)}"
        )
        return (
            None,
            [],
            {
                "erro": "Coluna de tarifa não encontrada no arquivo",
                "colunas_detectadas": list(df.columns),
                "indices_testados": indices_testados,
                "dica": "Informe coluna_tarifa com o nome exato da coluna (veja as linhas com 'preview')",
                "sucesso": False,
            },
        )

    if nomes["data"] is None:
        logger.error(
            f"Coluna de DATA não encontrada (palavras: {PALAVRAS_DATA}). Colunas: {list(df.columns)}"
        )
        return (
            None,
            [],
            {
                "erro": "Coluna de data de vigência não encontrada",
                "colunas_detectadas": list(df.columns),
                "dica": "Informe coluna_data com o nome exato da coluna de início da vigência (veja as linhas com 'preview')",
                "sucesso": False,
            },
        )

    return (
        _Colunas(
            tarifa=nomes["tarifa"], data=nomes["data"], descricao=nomes["descricao"]
        ),
        inferidas,
        None,
    )


def executar_leitura_tarifa(
    df: pd.DataFrame,
    consulta_tipo: str,
    ano: int | None = None,
    path: str = "",
    coluna_tarifa: str | None = None,
    coluna_data: str | None = None,
    coluna_descricao: str | None = None,
    linha_cabecalho: int | None = None,
) -> dict[str, Any]:
    """
    Lê tarifas históricas de concessionárias (MetrôRio, CCR Barcas, SuperVia).
    As colunas podem ser informadas (recomendado) ou inferidas.

    Tipos de consulta:
    1. 'atual' → Retorna TODAS as tarifas atuais (normal, social, etc)
    2. 'ano' → Retorna TODAS as tarifas vigentes em um ano específico
    3. 'ultima_mudanca' → Quando foi a última alteração
    4. 'historico' → Retorna histórico completo
    5. 'buscar_por_valor' → Busca tarifas abaixo de um valor

    Args:
        df: DataFrame com histórico de tarifas
        consulta_tipo: 'atual', 'ano', 'ultima_mudanca', 'historico', 'buscar_por_valor'
        ano: Ano a buscar (para 'ano') ou valor máximo (para 'buscar_por_valor')
        path: Caminho do arquivo
        coluna_tarifa: coluna com o valor da tarifa (None = inferir)
        coluna_data: coluna com o início da vigência (None = inferir)
        coluna_descricao: coluna que identifica/descreve cada tarifa, ex.: a linha (None = inferir)
        linha_cabecalho: posição da linha com os nomes reais das colunas (None = adivinhar)

    Returns:
        Dict com resultado formatado. Inclui `colunas_usadas` e, se alguma coluna foi inferida, um `aviso`.
    """
    logger.info(f"LEITURA_TARIFA | consulta: {consulta_tipo} | shape: {df.shape}")

    if linha_cabecalho is not None and not (0 <= linha_cabecalho < len(df)):
        return {
            "erro": f"linha_cabecalho={linha_cabecalho} fora do intervalo: o arquivo tem {len(df)} linhas (0 a {len(df) - 1})",
            "sucesso": False,
        }

    df = _limpar_e_renomear_colunas(df, linha_cabecalho)

    cols, inferidas, erro = _definir_colunas(
        df, coluna_tarifa, coluna_data, coluna_descricao
    )
    if erro:
        return erro
    logger.info(
        f"Colunas: tarifa={cols.tarifa} | data={cols.data} | descrição={cols.descricao}"
    )

    # Preparar dados: data e tarifa válidas
    df = df.assign(
        **{cols.data: pd.to_datetime(df[cols.data], errors="coerce", format="%d/%m/%Y")}
    ).dropna(subset=[cols.data])
    df = df.assign(
        **{cols.tarifa: pd.to_numeric(df[cols.tarifa], errors="coerce")}
    ).dropna(subset=[cols.tarifa])
    logger.debug(f"Registros válidos: {len(df)}")

    if df.empty:
        logger.error("Nenhum dado válido encontrado")
        return {
            "erro": "Nenhum dado de tarifa válido encontrado",
            "sucesso": False,
        }

    df = df.assign(_ano=df[cols.data].dt.year).sort_values(
        by=cols.data, ascending=False
    )

    consulta = _CONSULTAS.get(consulta_tipo)
    if consulta is None:
        logger.error(f"Tipo de consulta desconhecido: {consulta_tipo}")
        return {
            "erro": f"Tipo de consulta desconhecido: {consulta_tipo}",
            "tipos_disponiveis": ["atual", "ano", "ultima_mudanca", "historico"],
            "sucesso": False,
        }

    resultado = consulta(df, cols, ano, path)

    if resultado.get("sucesso"):
        resultado["colunas_usadas"] = {
            "tarifa": cols.tarifa,
            "data": cols.data,
            "descricao": cols.descricao,
        }
        if inferidas:
            resultado["aviso"] = (
                f"Colunas inferidas automaticamente: {', '.join(inferidas)}. Se não forem as certas, chame de novo "
                f"informando coluna_tarifa, coluna_data e coluna_descricao (e linha_cabecalho, se o cabeçalho não "
                f"for a primeira linha). Use 'preview' para ver as linhas do arquivo."
            )
    return resultado
