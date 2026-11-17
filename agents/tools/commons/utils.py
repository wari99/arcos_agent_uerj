import codecs
import io
import os
import re
import shutil
import traceback
import zipfile

import pandas as pd

from agents.tools.commons.core import logger
from agents.tools.commons.settings import (
    AMOSTRA_DETECCAO,
    ENCODING_PADRAO,
    ENCODINGS_SUPORTADOS,
    LIMIAR_SEPARADOR,
    REGEX_PATTERNS,
    SEPARADORES_CSV,
)


class _EstadoCache:
    """
    Centraliza o estado que antes eram as variáveis globais
    `_pasta_temporaria_global` e `_cache_arquivos`.
    Como é um único objeto compartilhado, mutações são vistas por todos os módulos.
    """

    def __init__(self):
        self.pasta_temporaria_global: str | None = None
        self.cache_arquivos: dict[str, dict] = {}


_estado = _EstadoCache()


def obter_pasta_temporaria() -> str | None:
    """Retorna o caminho da pasta temporária atual"""
    return _estado.pasta_temporaria_global


def obter_cache_arquivos() -> dict:
    """Retorna o cache de arquivos para outras tools"""
    return _estado.cache_arquivos


def listar_cache_arquivos() -> dict:
    """Lista arquivos atualmente no cache"""
    arquivos_cache = []
    total_mb = 0

    for info in _estado.cache_arquivos.values():
        if os.path.exists(info["path"]):
            arquivos_cache.append(
                {
                    "nome": info["nome"],
                    "linhas": info["linhas"],
                    "colunas": info["colunas"],
                    "tamanho_mb": info["tamanho_mb"],
                    "tipo_arquivo": info.get("tipo_arquivo", "desconhecido"),
                    "path": info["path"],
                }
            )
            total_mb += info["tamanho_mb"]

    logger.debug(
        f"Cache: {len(arquivos_cache)} arquivo(s), {round(total_mb, 2)} MB total"
    )
    return {
        "total_arquivos_cache": len(arquivos_cache),
        "total_tamanho_mb": round(total_mb, 2),
        "arquivos": arquivos_cache,
    }


def limpar_pasta_temporaria_manual() -> dict:
    """Limpa pasta temporária e cache"""
    logger.debug(f"DEBUG: _pasta_temporaria_global = {_estado.pasta_temporaria_global}")
    logger.debug(
        f"DEBUG: Existe? {os.path.exists(_estado.pasta_temporaria_global) if _estado.pasta_temporaria_global else False}"
    )

    if not (
        _estado.pasta_temporaria_global
        and os.path.exists(_estado.pasta_temporaria_global)
    ):
        logger.info("Nenhuma pasta temporária para limpar")
        return {"status": "info", "mensagem": "Nenhuma pasta temporária para remover"}

    try:
        logger.info(f"Removendo pasta temporária: {_estado.pasta_temporaria_global}")
        shutil.rmtree(_estado.pasta_temporaria_global)
        logger.info(f"Pasta removida com sucesso: {_estado.pasta_temporaria_global}")

        _estado.pasta_temporaria_global = None
        _estado.cache_arquivos.clear()
        logger.info("Cache limpo")

        return {"status": "sucesso", "mensagem": "Pasta e cache removidos"}
    except Exception as e:
        logger.error(f"Erro ao remover pasta: {e}")
        return {"status": "erro", "mensagem": f"Erro ao remover: {e}"}


# =============== FUNCOES DE FILTRO


def filtro_deteccao_padrao_estrutural(recursos: list, file_filter: str) -> list:
    """
    Filtra recursos por detecção de padrão estrutural.

    - YYYY_MM (sem dia) → prioriza arquivos que NÃO têm YYYY_MM_DD no nome
    - YYYY_MM_DD (com dia) → busca apenas arquivos com aquele dia
    - Outros → busca genérica (contains)
    """
    if not file_filter or not file_filter.strip():
        return recursos

    filtro_lower = file_filter.lower().strip()
    match_data = re.search(REGEX_PATTERNS["data_filtro"], filtro_lower)

    # REGRA 1: Data completa YYYY_MM_DD -> arquivo daquele dia
    if match_data and match_data.group(4):
        data_str = f"{match_data.group(1)}_{match_data.group(2)}_{match_data.group(4)}"
        resultado = [r for r in recursos if data_str in r.get("name", "")]
        logger.info(f"Padrão: dia {data_str} → {len(resultado)} arquivo(s)")
        return resultado

    # REGRA 2: Apenas mês YYYY_MM -> prioriza arquivos SEM dia no nome
    if match_data and not match_data.group(4):
        data_str = f"{match_data.group(1)}_{match_data.group(2)}"

        # Separar: arquivos que TÊM o mês mas NÃO têm dia (padrão mensal/consolidado)
        mensais = [
            r
            for r in recursos
            if data_str in r.get("name", "")
            and not re.search(REGEX_PATTERNS["data_completa_nome"], r.get("name", ""))
        ]

        # Arquivos que TÊM o mês E têm dia (padrão diário)
        diarios = [
            r
            for r in recursos
            if data_str in r.get("name", "")
            and re.search(REGEX_PATTERNS["data_completa_nome"], r.get("name", ""))
        ]

        if mensais:
            logger.info(
                f"Padrão: mês {data_str} → {len(mensais)} arquivo(s) mensal(is)"
            )
            return mensais

        logger.warning(
            f"Padrão: mês {data_str} → sem mensal, usando {len(diarios)} diário(s)"
        )
        return diarios

    # REGRA 3: Busca genérica
    resultado = [r for r in recursos if filtro_lower in r.get("name", "").lower()]
    logger.info(f"Filtro genérico '{filtro_lower}' → {len(resultado)} arquivo(s)")
    return resultado


def _ano_mes(texto: str):
    """(ano, mês) da primeira data YYYY_MM no texto, ou None."""
    m = re.search(REGEX_PATTERNS["data_filtro"], texto)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _rotulo_mes(ano_mes) -> str:
    return f"{ano_mes[0]}_{ano_mes[1]:02d}"


def resolver_consolidado_do_mes(recursos: list, file_filter: str):
    """
    Pedido de arquivo CONSOLIDADO de um mês (filtro com 'consolidado' e YYYY_MM, sem dia).

    Retorna None se o filtro não for esse tipo de pedido (use filtro_deteccao_padrao_estrutural).
    Senão, (recursos, erro):
      - o mês existe → (arquivos do mês, None)
      - o mês NÃO existe → ([], mensagem). Nunca troca de mês por conta própria: a mensagem informa que
        não existe, sugere o próximo mês disponível e manda perguntar ao usuário antes de usá-lo.
    """
    filtro = (file_filter or "").lower().strip()
    if "consolidado" not in filtro:
        return None
    m = re.search(REGEX_PATTERNS["data_filtro"], filtro)
    if not m or m.group(4):
        return None
    pedido = (int(m.group(1)), int(m.group(2)))

    por_mes: dict[tuple, list] = {}
    for r in recursos:
        nome = r.get("name", "")
        if "consolidado" not in nome.lower() or re.search(
            REGEX_PATTERNS["data_completa_nome"], nome
        ):
            continue
        ano_mes = _ano_mes(nome)
        if ano_mes:
            por_mes.setdefault(ano_mes, []).append(r)

    if pedido in por_mes:
        logger.info(
            f"Padrão: consolidado {_rotulo_mes(pedido)} → {len(por_mes[pedido])} arquivo(s)"
        )
        return por_mes[pedido], None

    seguintes = sorted(k for k in por_mes if k > pedido)
    if seguintes:
        sugerido = _rotulo_mes(seguintes[0])
        mensagem = (
            f"Não existe consolidado de {_rotulo_mes(pedido)} na base. O próximo mês disponível é {sugerido}. "
            f"Informe ao usuário que {_rotulo_mes(pedido)} não existe e pergunte se ele quer usar {sugerido}; "
            f"NÃO consulte outro mês sem essa confirmação."
        )
    else:
        ultimo = _rotulo_mes(max(por_mes)) if por_mes else "nenhum"
        mensagem = (
            f"Não existe consolidado de {_rotulo_mes(pedido)} na base, nem de meses seguintes "
            f"(último consolidado disponível: {ultimo}). Informe isso ao usuário."
        )
    logger.warning(f"Padrão: {mensagem}")
    return [], mensagem


# =============== FUNCOES INTERNAS - ENCODING


def _detectar_encoding(conteudo_bytes: bytes, parcial: bool = False) -> str:
    """
    Detecta encoding do arquivo testando sequencialmente.
    parcial=True: os bytes são só o começo do arquivo, então um caractere multibyte cortado no fim
    não pode reprovar o UTF-8 (antes isso fazia o arquivo inteiro ser lido como latin-1).
    """
    for encoding in ENCODINGS_SUPORTADOS:
        try:
            if parcial:
                codecs.getincrementaldecoder(encoding)().decode(
                    conteudo_bytes, final=False
                )
            else:
                conteudo_bytes.decode(encoding)
            if encoding != ENCODING_PADRAO:
                logger.debug(f"Encoding detectado: {encoding}")
            return encoding
        except UnicodeDecodeError:
            continue

    logger.warning("Usando UTF-8 com substituição de caracteres")
    return ENCODING_PADRAO


def _detectar_separador(amostra: str) -> str:
    """Detecta melhor separador para CSV"""
    contadores = {sep: amostra.count(sep) for sep in SEPARADORES_CSV}

    separador_melhor = max(contadores, key=contadores.get)

    if contadores[separador_melhor] < LIMIAR_SEPARADOR:
        separador_melhor = ";"

    if separador_melhor == ";":
        logger.debug("Separador: ponto-e-vírgula")
    elif separador_melhor == ",":
        logger.debug("Separador: vírgula")
    else:
        logger.debug("Separador: tabulação")

    return separador_melhor


# =============== FUNCOES INTERNAS - PROCESSAR ARQUIVOS


def _processar_xlsx(conteudo_bytes: bytes) -> pd.DataFrame | None:
    """
    Processa arquivo XLSX (Excel).

    Características:
    - Lê a primeira planilha por padrão
    - Detecta cabeçalhos automaticamente
    - Trata valores vazios
    - Limpa colunas/linhas totalmente vazias

    Args:
        conteudo_bytes: Conteúdo do arquivo em bytes

    Returns:
        DataFrame ou None se falhar
    """
    try:
        arquivo_bytes = io.BytesIO(conteudo_bytes)

        df = pd.read_excel(arquivo_bytes, sheet_name=0, engine="openpyxl", header=0)

        logger.info(f"XLSX processado: {len(df)} linhas, {len(df.columns)} colunas")
        colunas_preview = list(df.columns)[:5]
        logger.debug(
            f"Primeiras colunas: {colunas_preview}..."
            if len(df.columns) > 5
            else f"Colunas: {colunas_preview}"
        )

        if df.empty:
            logger.warning("XLSX está vazio (sem dados)")
            return None

        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0, how="all")

        if df.empty:
            logger.error("XLSX não contém dados válidos após limpeza")
            return None

        logger.info(f"Após limpeza: {len(df)} linhas, {len(df.columns)} colunas")
        return df

    except Exception as e:
        logger.error(f"Erro ao processar XLSX: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None


def _processar_csv(conteudo_bytes: bytes) -> pd.DataFrame | None:
    """Processa arquivo CSV com detecção de encoding e separador"""
    try:
        encoding = _detectar_encoding(conteudo_bytes)
        amostra = conteudo_bytes[:10000].decode(encoding, errors="ignore")
        separador = _detectar_separador(amostra)

        logger.debug(f"Encoding: {encoding}")
        logger.debug(f"Separador: {separador}")

        df = pd.read_csv(
            io.BytesIO(conteudo_bytes),
            encoding=encoding,
            sep=separador,
            on_bad_lines="skip",
            engine="python",
        )

        if df is not None and not df.empty:
            logger.info(f"CSV processado: {len(df)} linhas, {len(df.columns)} colunas")
            return df
        else:
            logger.warning("CSV está vazio ou None")
            return None

    except Exception as e:
        logger.error(f"Erro ao processar CSV: {e!s}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None


def _processar_zip(conteudo_bytes: bytes) -> pd.DataFrame | None:
    """Extrai e processa CSV de ZIP"""
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo_bytes)) as zip_ref:
            csvs = [f for f in zip_ref.namelist() if f.lower().endswith(".csv")]

            if not csvs:
                logger.error("ZIP não contém CSV")
                return None

            arquivo_csv = csvs[0]
            logger.info(f"Extraindo CSV do ZIP: {arquivo_csv}")

            with zip_ref.open(arquivo_csv) as f:
                conteudo_amostra = f.read()[:AMOSTRA_DETECCAO]
                encoding = _detectar_encoding(conteudo_amostra, parcial=True)
                f.seek(0)
                conteudo = f.read().decode(encoding, errors="replace")

                separador = _detectar_separador(conteudo[:AMOSTRA_DETECCAO])
                df = pd.read_csv(io.StringIO(conteudo), sep=separador)

                logger.info(
                    f"ZIP processado: {len(df)} linhas, {len(df.columns)} colunas"
                )
                return df

    except zipfile.BadZipFile:
        logger.error("ZIP corrompido ou inválido")
        return None
    except Exception as e:
        logger.error(f"Erro ao processar ZIP: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None
