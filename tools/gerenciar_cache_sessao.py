import os
import shutil
from typing import Any, Dict, List
from langchain.tools import tool

import traceback

from tools.commons.core import logger
from tools.baixar_arquivo_dados import baixar_arquivo_dados

from tools.commons.utils import (
    obter_pasta_temporaria,
    obter_cache_arquivos,
    limpar_pasta_temporaria_manual,
)

def obter_arquivos_para_analise(
    package_id: str,
    file_filter: str = "",
    força_download: bool = False
) -> Dict[str, Any]:
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
        logger.info("OBTER_ARQUIVOS_PARA_ANALISE - INÍCIO")
        logger.info(f"Package ID: {package_id}")
        logger.info(f"Filtro: {file_filter if file_filter else '(nenhum)'}")
        logger.info(f"Força download: {força_download}")
        
        arquivos_para_analisar: List[Dict] = []
        
        # ============================================================
        # PASSO 1: Tentar obter do cache (exceto se força_download)
        # ============================================================
        if not força_download:
            logger.info("Procurando no cache...")
            
            try:
                cache_arquivos = obter_cache_arquivos()
                logger.info(f"Cache obtido: {len(cache_arquivos)} arquivos")
                
                for info_cache in cache_arquivos.values():
                    nome_arquivo = info_cache.get("nome", "")
                    
                    if file_filter and file_filter.lower() not in nome_arquivo.lower():
                        continue
                    
                    if os.path.exists(info_cache["path"]):
                        arquivos_para_analisar.append({
                            "nome": nome_arquivo,
                            "df": info_cache["dataframe"],
                            "path": info_cache["path"],
                            "do_cache": True,
                        })
                        logger.info(f"{nome_arquivo} (do cache)")
                
                if arquivos_para_analisar:
                    logger.info(f"{len(arquivos_para_analisar)} arquivo(s) encontrado(s) no cache!")
                    return {
                        "arquivos": arquivos_para_analisar,
                        "total_arquivos": len(arquivos_para_analisar),
                        "do_cache": True,
                        "sucesso": True
                    }
                
                logger.info("Nenhum arquivo no cache, baixando...")
                
            except Exception as e:
                logger.warning(f"Erro ao acessar cache: {e}")
                logger.warning("Tentando download mesmo assim...")
        

        logger.info("Baixando arquivo(s)...")
        try:
            resultado_download = baixar_arquivo_dados({
                "package_id": package_id,
                "file_filter": file_filter,
            })
            
            logger.info("Download concluído")
            
        except Exception as e:
            error_msg = f"Erro durante download: {str(e)}"
            logger.error(error_msg)
            return {
                "erro": error_msg,
                "sucesso": False,
                "traceback": traceback.format_exc()
            }
        
        if not isinstance(resultado_download, dict) or "erro" in resultado_download:
            erro_msg = (
                resultado_download.get("erro", "Erro desconhecido")
                if isinstance(resultado_download, dict)
                else "Resposta inválida"
            )
            logger.error(f"Erro no download: {erro_msg}")
            return {
                "erro": f"Falha no download: {erro_msg}",
                "sucesso": False
            }
        

        logger.info("Atualizando cache...")
        try:
            cache_arquivos = obter_cache_arquivos()
            logger.info(f"Cache atualizado: {len(cache_arquivos)} arquivos")
            
            for nome, info in resultado_download.items():
                if nome == "_resumo_processamento":
                    continue
                if not isinstance(info, dict) or not info.get("sucesso"):
                    continue
                
                for info_cache in cache_arquivos.values():
                    if info_cache["nome"] == nome:
                        if os.path.exists(info_cache["path"]):
                            arquivos_para_analisar.append({
                                "nome": nome,
                                "df": info_cache["dataframe"],
                                "path": info_cache["path"],
                                "do_cache": False,  
                            })
                            logger.info(f"{nome} (baixado)")
                        break
            
        except Exception as e:
            error_msg = f"Erro ao processar cache após download: {str(e)}"
            logger.error(error_msg)
            return {
                "erro": error_msg,
                "sucesso": False,
                "traceback": traceback.format_exc()
            }
        
        if not arquivos_para_analisar:
            logger.error("Nenhum arquivo disponível após download")
            return {
                "erro": "Nenhum arquivo disponível para análise",
                "detalhes": f"package_id={package_id}, file_filter='{file_filter}'",
                "sucesso": False
            }
        
        logger.info(f"{len(arquivos_para_analisar)} arquivo(s) pronto(s) para análise!")
        
        return {
            "arquivos": arquivos_para_analisar,
            "total_arquivos": len(arquivos_para_analisar),
            "do_cache": False,  # Acabou de baixar
            "sucesso": True
        }
        
    except Exception as e:
        error_msg = f"Erro crítico em obter_arquivos_para_analise: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "erro": error_msg,
            "traceback": traceback.format_exc(),
            "sucesso": False
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
            package_id = params.get("package_id")
            file_filter = params.get("file_filter", "")
            força_download = params.get("força_download", False)
            
            if not package_id:
                return {
                    "erro": "Parâmetro 'package_id' é obrigatório",
                    "sucesso": False
                }
            
            return obter_arquivos_para_analise(
                package_id=package_id,
                file_filter=file_filter,
                força_download=força_download
            )
                
        pasta_temp = obter_pasta_temporaria()
        
        if not pasta_temp or not os.path.exists(pasta_temp):
            logger.warning("Nenhuma pasta temporária ativa")
            return {
                "acao": acao,
                "status": "info",
                "mensagem": "Nenhuma pasta temporária ativa"
            }

        if acao == "listar":
            logger.info(f"Listando arquivos em: {pasta_temp}")
            arquivos = []
            total_tamanho = 0
            
            for item in os.listdir(pasta_temp):
                caminho_completo = os.path.join(pasta_temp, item)
                if os.path.isfile(caminho_completo):
                    tamanho = os.path.getsize(caminho_completo)
                    total_tamanho += tamanho
                    
                    arquivos.append({
                        "nome": item,
                        "tamanho_bytes": tamanho,
                        "tamanho_mb": round(tamanho / (1024*1024), 2),
                        "caminho_completo": caminho_completo
                    })
                    logger.debug(f"Arquivo encontrado: {item} ({round(tamanho / (1024*1024), 2)} MB)")
            
            logger.info(f"Total: {len(arquivos)} arquivo(s), {round(total_tamanho / (1024*1024), 2)} MB")
            return {
                "acao": "listar",
                "pasta_temporaria": pasta_temp,
                "total_arquivos": len(arquivos),
                "total_tamanho_mb": round(total_tamanho / (1024*1024), 2),
                "arquivos": arquivos,
                "sucesso": True
            }

        elif acao == "info":
            logger.info(f"Obtendo informações de: {pasta_temp}")
            
            if not os.path.exists(pasta_temp):
                logger.warning("Pasta temporária não existe")
                return {
                    "acao": "info",
                    "status": "pasta_inexistente",
                    "mensagem": "Pasta temporária não existe"
                }
            
            total_arquivos = 0
            total_tamanho = 0
            
            for item in os.listdir(pasta_temp):
                caminho_completo = os.path.join(pasta_temp, item)
                if os.path.isfile(caminho_completo):
                    total_arquivos += 1
                    total_tamanho += os.path.getsize(caminho_completo)
            
            logger.info(f"Info: {total_arquivos} arquivo(s), {round(total_tamanho / (1024*1024), 2)} MB")
            return {
                "acao": "info",
                "pasta_temporaria": pasta_temp,
                "total_arquivos": total_arquivos,
                "total_tamanho_mb": round(total_tamanho / (1024*1024), 2),
                "pasta_existe": True,
                "sucesso": True
            }

        elif acao == "limpar":
            logger.info("Limpando pasta temporária...")
            resultado_limpeza = limpar_pasta_temporaria_manual()
            
            if resultado_limpeza.get("status") == "sucesso":
                logger.info("Pasta temporária limpada com sucesso")
            else:
                logger.warning(f"Erro ao limpar: {resultado_limpeza}")
            
            return {
                "acao": "limpar",
                "resultado": resultado_limpeza,
                "sucesso": resultado_limpeza.get("status") == "sucesso"
            }

        elif acao == "remover_arquivo":
            arquivo_especifico = params.get("arquivo")
            
            if not arquivo_especifico:
                logger.error("Nome do arquivo não especificado")
                return {
                    "acao": "remover_arquivo",
                    "erro": "É necessário especificar o nome do arquivo",
                    "sucesso": False
                }
            
            caminho_arquivo = os.path.join(pasta_temp, arquivo_especifico)
            
            if not os.path.exists(caminho_arquivo):
                logger.error(f"Arquivo não encontrado: {arquivo_especifico}")
                return {
                    "acao": "remover_arquivo",
                    "arquivo": arquivo_especifico,
                    "erro": "Arquivo não encontrado",
                    "sucesso": False
                }
            
            try:
                os.remove(caminho_arquivo)
                logger.info(f"Arquivo removido: {arquivo_especifico}")
                return {
                    "acao": "remover_arquivo",
                    "arquivo": arquivo_especifico,
                    "mensagem": f"Arquivo '{arquivo_especifico}' removido com sucesso",
                    "sucesso": True
                }
            except Exception as e:
                logger.error(f"Erro ao remover arquivo: {str(e)}")
                return {
                    "acao": "remover_arquivo",
                    "arquivo": arquivo_especifico,
                    "erro": f"Erro ao remover arquivo: {str(e)}",
                    "sucesso": False
                }

        else:
            logger.error(f"Ação desconhecida: {acao}")
            return {
                "erro": f"Ação desconhecida: {acao}",
                "acoes_disponiveis": ["listar", "info", "limpar", "remover_arquivo", "obter_para_analise"],
                "sucesso": False
            }

    except Exception as e:
        logger.error(f"Erro no gerenciamento de cache: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "erro": f"Erro no gerenciamento de cache: {str(e)}",
            "sucesso": False
        }