import os
import traceback
from collections.abc import Callable
from typing import Any

from langchain.tools import tool

from agents.sub_agents.analysis.tools.baixar_arquivo_dados import baixar_arquivo_dados
from agents.tools.commons.core import logger
from agents.tools.commons.utils import (
    limpar_pasta_temporaria_manual,
    obter_cache_arquivos,
    obter_pasta_temporaria,
)

# (package_id, file_filter) -> aviso de arquivos omitidos pelo MAX_ARQUIVOS no último download.
# Permite avisar também quando a consulta seguinte for atendida só pelo cache.
_AVISOS_OMITIDOS: dict[tuple, str] = {}

ACOES_DISPONIVEIS = [
    "listar",
    "info",
    "limpar",
    "remover_arquivo",
    "obter_para_analise",
]


def _mb(tamanho_bytes: int) -> float:
    return round(tamanho_bytes / (1024 * 1024), 2)


def _item_arquivo(info_cache: dict, do_cache: bool) -> dict:
    """Entrada do cache no formato devolvido para análise."""
    return {
        "nome": info_cache["nome"],
        "df": info_cache["dataframe"],
        "path": info_cache["path"],
        "do_cache": do_cache,
        # memória do DataFrame, já calculada ao baixar (evita recalcular a cada consulta)
        "memoria_mb": info_cache.get("memoria_mb"),
        # dicionário que vive junto com o arquivo no cache: guarda cálculos reaproveitáveis (ex.: turnos)
        "memo": info_cache.setdefault("memo", {}),
    }


def _arquivos_da_pasta(pasta: str) -> list[dict]:
    """Arquivos (não diretórios) da pasta, com tamanho."""
    arquivos = []
    for item in os.listdir(pasta):
        caminho = os.path.join(pasta, item)
        if os.path.isfile(caminho):
            tamanho = os.path.getsize(caminho)
            arquivos.append(
                {
                    "nome": item,
                    "tamanho_bytes": tamanho,
                    "tamanho_mb": _mb(tamanho),
                    "caminho_completo": caminho,
                }
            )
    return arquivos


def obter_arquivos_para_analise(
    package_id: str, file_filter: str = "", força_download: bool = False
) -> dict[str, Any]:
    """
    Obtém arquivos prontos para análise.

    Centraliza toda a lógica de:
    - Verificar cache
    - Baixar se necessário
    - Validar arquivos

    Args:
        package_id: ID da base
        file_filter: Filtro de nome de arquivo
        força_download: Se True, ignora cache e baixa novamente

    Returns:
        {
            "arquivos": [{"nome": "...", "df": ..., "path": "..."}],
            "total_arquivos": int,
            "do_cache": bool,
            "erro": str (se houver),
            "sucesso": bool
        }
    """
    try:
        logger.info(
            f"OBTER_ARQUIVOS_PARA_ANALISE | package_id={package_id} | "
            f"filtro={file_filter or '(nenhum)'} | força_download={força_download}"
        )

        # PASSO 1: cache (exceto se força_download)
        if not força_download:
            try:
                cache_arquivos = obter_cache_arquivos()
                logger.debug(f"Cache obtido: {len(cache_arquivos)} arquivos")

                do_cache = [
                    _item_arquivo(info, True)
                    for info in cache_arquivos.values()
                    if (
                        not file_filter
                        or file_filter.lower() in info.get("nome", "").lower()
                    )
                    and os.path.exists(info["path"])
                ]
                if do_cache:
                    logger.info(
                        f"{len(do_cache)} arquivo(s) encontrado(s) no cache: {[a['nome'] for a in do_cache]}"
                    )
                    resultado = {
                        "arquivos": do_cache,
                        "total_arquivos": len(do_cache),
                        "do_cache": True,
                        "sucesso": True,
                    }
                    aviso = _AVISOS_OMITIDOS.get((package_id, file_filter))
                    if aviso:
                        resultado["aviso"] = aviso
                    return resultado
                logger.info("Nenhum arquivo no cache, baixando...")

            except Exception as e:
                logger.warning(
                    f"Erro ao acessar cache: {e}. Tentando download mesmo assim..."
                )

        # PASSO 2: download
        resultado_download = baixar_arquivo_dados(
            {
                "package_id": package_id,
                "file_filter": file_filter,
            }
        )

        if not isinstance(resultado_download, dict) or "erro" in resultado_download:
            erro_msg = (
                resultado_download.get("erro", "Erro desconhecido")
                if isinstance(resultado_download, dict)
                else "Resposta inválida"
            )
            logger.error(f"Erro no download: {erro_msg}")
            return {"erro": f"Falha no download: {erro_msg}", "sucesso": False}

        # PASSO 3: cache atualizado -> arquivos baixados (índice por nome em vez de varredura por arquivo)
        cache_por_nome = {
            info["nome"]: info for info in obter_cache_arquivos().values()
        }
        baixados = [
            _item_arquivo(cache_por_nome[nome], False)
            for nome, info in resultado_download.items()
            if nome != "_resumo_processamento"
            and isinstance(info, dict)
            and info.get("sucesso")
            and nome in cache_por_nome
            and os.path.exists(cache_por_nome[nome]["path"])
        ]

        if not baixados:
            logger.error("Nenhum arquivo disponível após download")
            return {
                "erro": "Nenhum arquivo disponível para análise",
                "detalhes": f"package_id={package_id}, file_filter='{file_filter}'",
                "sucesso": False,
            }

        logger.info(
            f"{len(baixados)} arquivo(s) pronto(s) para análise: {[a['nome'] for a in baixados]}"
        )
        resultado = {
            "arquivos": baixados,
            "total_arquivos": len(baixados),
            "do_cache": False,  # Acabou de baixar
            "sucesso": True,
        }
        aviso = resultado_download.get("_resumo", {}).get("aviso")
        if aviso:
            _AVISOS_OMITIDOS[(package_id, file_filter)] = aviso
            resultado["aviso"] = aviso
        else:
            _AVISOS_OMITIDOS.pop((package_id, file_filter), None)
        return resultado

    except Exception as e:
        # traceback só no log: no retorno ele iria para o contexto do modelo
        logger.error(
            f"Erro crítico em obter_arquivos_para_analise: {e}\n{traceback.format_exc()}"
        )
        return {
            "erro": f"Erro crítico em obter_arquivos_para_analise: {e}",
            "sucesso": False,
        }


# AÇÕES DA TOOL
def _acao_obter_para_analise(params: dict, pasta_temp: str = "") -> dict:
    package_id = params.get("package_id")
    if not package_id:
        return {"erro": "Parâmetro 'package_id' é obrigatório", "sucesso": False}

    # aceita com e sem cedilha: o modelo pode errar a grafia no JSON
    força_download = params.get("força_download", params.get("forca_download", False))
    return obter_arquivos_para_analise(
        package_id=package_id,
        file_filter=params.get("file_filter", ""),
        força_download=força_download,
    )


def _acao_listar(params: dict, pasta_temp: str) -> dict:
    arquivos = _arquivos_da_pasta(pasta_temp)
    total_mb = _mb(sum(a["tamanho_bytes"] for a in arquivos))
    logger.info(f"Listagem de {pasta_temp}: {len(arquivos)} arquivo(s), {total_mb} MB")
    return {
        "acao": "listar",
        "pasta_temporaria": pasta_temp,
        "total_arquivos": len(arquivos),
        "total_tamanho_mb": total_mb,
        "arquivos": arquivos,
        "sucesso": True,
    }


def _acao_info(params: dict, pasta_temp: str) -> dict:
    arquivos = _arquivos_da_pasta(pasta_temp)
    total_mb = _mb(sum(a["tamanho_bytes"] for a in arquivos))
    logger.info(f"Info de {pasta_temp}: {len(arquivos)} arquivo(s), {total_mb} MB")
    return {
        "acao": "info",
        "pasta_temporaria": pasta_temp,
        "total_arquivos": len(arquivos),
        "total_tamanho_mb": total_mb,
        "pasta_existe": True,
        "sucesso": True,
    }


def _acao_limpar(params: dict, pasta_temp: str) -> dict:
    resultado = limpar_pasta_temporaria_manual()
    sucesso = resultado.get("status") == "sucesso"
    if sucesso:
        logger.info("Pasta temporária limpada com sucesso")
    else:
        logger.warning(f"Erro ao limpar: {resultado}")
    return {"acao": "limpar", "resultado": resultado, "sucesso": sucesso}


def _acao_remover_arquivo(params: dict, pasta_temp: str) -> dict:
    arquivo = params.get("arquivo")
    if not arquivo:
        logger.error("Nome do arquivo não especificado")
        return {
            "acao": "remover_arquivo",
            "erro": "É necessário especificar o nome do arquivo",
            "sucesso": False,
        }

    caminho = os.path.join(pasta_temp, arquivo)
    if not os.path.exists(caminho):
        logger.error(f"Arquivo não encontrado: {arquivo}")
        return {
            "acao": "remover_arquivo",
            "arquivo": arquivo,
            "erro": "Arquivo não encontrado",
            "sucesso": False,
        }

    try:
        os.remove(caminho)
    except Exception as e:
        logger.error(f"Erro ao remover arquivo: {e}")
        return {
            "acao": "remover_arquivo",
            "arquivo": arquivo,
            "erro": f"Erro ao remover arquivo: {e}",
            "sucesso": False,
        }

    logger.info(f"Arquivo removido: {arquivo}")
    return {
        "acao": "remover_arquivo",
        "arquivo": arquivo,
        "mensagem": f"Arquivo '{arquivo}' removido com sucesso",
        "sucesso": True,
    }


# ações que operam sobre a pasta temporária da sessão
_ACOES_NA_PASTA: dict[str, Callable[[dict, str], dict]] = {
    "listar": _acao_listar,
    "info": _acao_info,
    "limpar": _acao_limpar,
    "remover_arquivo": _acao_remover_arquivo,
}


@tool("gerenciar_cache_sessao")
def gerenciar_cache_sessao(params: dict) -> Any:
    """
    Gerencia arquivos baixados na pasta temporária da sessão.

    Parâmetros esperados em *params*:
    - acao (str): listar | limpar | info | remover_arquivo | obter_para_analise
    - arquivo (str): nome do arquivo específico (para acao=remover_arquivo)
    - package_id (str): para acao=obter_para_analise
    - file_filter (str): para acao=obter_para_analise
    - força_download (bool): para acao=obter_para_analise
    """
    try:
        acao = params.get("acao", "listar")

        if acao == "obter_para_analise":
            return _acao_obter_para_analise(params)

        if acao not in _ACOES_NA_PASTA:
            logger.error(f"Ação desconhecida: {acao}")
            return {
                "erro": f"Ação desconhecida: {acao}",
                "acoes_disponiveis": ACOES_DISPONIVEIS,
                "sucesso": False,
            }

        pasta_temp = obter_pasta_temporaria()
        if not pasta_temp or not os.path.exists(pasta_temp):
            logger.warning("Nenhuma pasta temporária ativa")
            return {
                "acao": acao,
                "status": "info",
                "mensagem": "Nenhuma pasta temporária ativa",
            }

        return _ACOES_NA_PASTA[acao](params, pasta_temp)

    except Exception as e:
        logger.error(f"Erro no gerenciamento de cache: {e}\n{traceback.format_exc()}")
        return {"erro": f"Erro no gerenciamento de cache: {e}", "sucesso": False}
