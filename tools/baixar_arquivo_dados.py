import os
import io
import tempfile
import requests
import pandas as pd
import hashlib
from typing import Any, Dict, Optional
from langchain.tools import tool
import re 
from dotenv import load_dotenv

from tools.commons.core import logger
from tools.commons.settings import (
    TIMEOUT_REQUISICAO,
    MAX_ARQUIVOS,
)
from tools.commons.utils import (
    _processar_xlsx,
    _processar_csv,
    _processar_zip,
    filtro_deteccao_padrao_estrutural,
    _estado
)

load_dotenv()

@tool("baixar_arquivo_dados")
def baixar_arquivo_dados(params: dict) -> Any:
    """Baixa e processa arquivos de uma base de dados"""
    
    try:
        package_id = params.get("package_id", "").strip()
        file_filter = params.get("file_filter", "").strip()
        
        if not package_id:
            return _criar_resposta_erro("Parâmetro 'package_id' obrigatório")
        
        logger.info("BAIXAR_ARQUIVO_DADOS - INÍCIO")
        logger.info(f"Base: '{package_id}' | Filtro: '{file_filter}'")
        
        url = os.getenv("URL_CONSULTAR_PROCESSAR_ARQUIVO").format(package_id)

        try:
            resp = requests.get(url, timeout=TIMEOUT_REQUISICAO)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro ao buscar API: {e}"
            logger.error(error_msg)
            return _criar_resposta_erro(error_msg)
        
        if not data.get("success"):
            error_msg = "Pacote não encontrado ou inacessível"
            logger.error(error_msg)
            return _criar_resposta_erro(error_msg)
        
        resources = data["result"].get("resources", [])
        
        if not resources:
            error_msg = "Nenhum recurso encontrado"
            logger.error(error_msg)
            return _criar_resposta_erro(error_msg)
        
        if file_filter:
            resources = filtro_deteccao_padrao_estrutural(resources, file_filter)
        
        if not resources:
            error_msg = f"Nenhum arquivo com filtro: '{file_filter}'"
            logger.error(error_msg)
            return _criar_resposta_erro(error_msg)
        
        resources = resources[:MAX_ARQUIVOS]
        logger.info(f"{len(resources)} arquivo(s) encontrado(s)")
        
        pasta_temp = _criar_pasta_temporaria()
        resultados = {}
        stats = {"sucesso": 0, "erro": 0, "cache": 0, "novos": 0}
        
        logger.info(f"PROCESSANDO {len(resources)} ARQUIVO(S)")
        
        for resource in resources:
            resultado = _baixar_e_processar_arquivo(resource, pasta_temp)
            nome = resource.get("name", "arquivo")
            
            if not resultado.get("sucesso"):
                resultados[nome] = resultado
                stats["erro"] += 1
                logger.warning(f"Erro ao processar: {nome}")
                continue
            
            df = resultado["df"]
            memoria_mb = df.memory_usage(deep=True).sum() / (1024*1024)
            
            resultados[nome] = {
                "linhas": len(df),
                "colunas": len(df.columns),
                "nomes_colunas": list(df.columns),
                "memoria_mb": round(memoria_mb, 2),
                "path": resultado["path"],
                "tipo_arquivo": resultado.get("tipo_arquivo", "desconhecido"),
                "do_cache": resultado.get("do_cache", False),
                "sucesso": True
            }
            
            stats["sucesso"] += 1
            if resultado.get("do_cache"):
                stats["cache"] += 1
            else:
                stats["novos"] += 1
        
        resultados["_resumo"] = {
            "pasta_temporaria": pasta_temp,
            "arquivos_solicitados": len(resources),
            "processados_com_sucesso": stats["sucesso"],
            "processados_com_erro": stats["erro"],
            "do_cache": stats["cache"],
            "downloads_novos": stats["novos"],
            "sucesso_geral": stats["sucesso"] > 0
        }
        
        logger.info(f"RESUMO: {stats['sucesso']} sucesso, {stats['erro']} erro")
        logger.info(f"Cache: {stats['cache']} | Novos: {stats['novos']}")
        
        return resultados
        
    except Exception as e:
        error_msg = f"Erro geral: {e}"
        logger.error(error_msg)
        logger.error(f"Traceback: {os.traceback.format_exc()}")
        return _criar_resposta_erro(error_msg)

# =============== FUNCOES INTERNAS DETECTAR TIPO

def _detectar_tipo_arquivo(nome: str, mimetype: str) -> str:
    """
    Detecta tipo de arquivo com prioridade correta
    """
    nome_lower = nome.lower()
    mime_lower = (mimetype or "").lower()
    
    logger.debug(f"Detecção: nome='{nome_lower}' | mime='{mime_lower}'")
    
    if nome_lower.endswith(".xlsx"):
        logger.debug("Detectado: XLSX (por extensão)")
        return "xlsx"
    
    if "spreadsheet" in mime_lower or "ms-excel" in mime_lower:
        logger.debug("Detectado: XLSX (por MIME type)")
        return "xlsx"
    
    if "openxmlformats" in mime_lower or "officedocument" in mime_lower:
        logger.debug("Detectado: XLSX (por MIME OpenXML)")
        return "xlsx"
    
    if nome_lower.endswith(".zip"):
        logger.debug("Detectado: ZIP (por extensão)")
        return "zip"
    
    if "zip" in mime_lower:
        logger.debug("Detectado: ZIP (por MIME type)")
        return "zip"
    
    if nome_lower.endswith(".csv"):
        logger.debug("Detectado: CSV (por extensão)")
        return "csv"
    
    if "csv" in mime_lower or "text/plain" in mime_lower:
        logger.debug("Detectado: CSV (por MIME type)")
        return "csv"
    
    if nome_lower.endswith(".pdf") or "pdf" in mime_lower:
        logger.warning(f"Tipo: PDF (não suportado) - {nome_lower}")
        return "pdf"
    
    logger.warning(f"Tipo desconhecido: {nome_lower}")
    return "desconhecido"

# =============== FUNCOES INTERNAS - CRIAR PASTA E CACHE

def _criar_pasta_temporaria() -> str:
    """Cria ou retorna pasta temporária existente"""
    if _estado.pasta_temporaria_global is None or not os.path.exists(_estado.pasta_temporaria_global):
        _estado.pasta_temporaria_global = tempfile.mkdtemp(prefix="arcos_rj_")
        logger.info(f"Pasta temporária criada: {_estado.pasta_temporaria_global}")

    return _estado.pasta_temporaria_global

def _gerar_chave_cache(url: str, nome: str) -> str:
    """Gera chave única para cache"""
    conteudo = f"{url}|{nome}"
    return hashlib.md5(conteudo.encode()).hexdigest()[:16]

def _arquivo_existe_no_cache(chave: str) -> Optional[Dict]:
    """Verifica se arquivo já foi baixado e ainda existe"""
    if chave not in _estado.cache_arquivos:
        return None

    info = _estado.cache_arquivos[chave]

    if not os.path.exists(info.get("path", "")):
        del _estado.cache_arquivos[chave]
        logger.warning(f"Arquivo de cache removido (arquivo não encontrado): {info.get('nome')}")
        return None

    logger.info(f"Arquivo encontrado em cache: {info['nome']}")
    return info

def _salvar_cache(chave: str, info: Dict) -> None:
    """Salva arquivo no cache"""
    _estado.cache_arquivos[chave] = info
    logger.debug(f"Arquivo salvo em cache: {info['nome']}")

def _validar_dataframe(df: Optional[pd.DataFrame]) -> bool:
    """Valida se DataFrame é válido"""
    return df is not None and not df.empty

def _criar_resposta_erro(mensagem: str) -> Dict:
    """Cria resposta padronizada de erro"""
    return {"erro": mensagem, "sucesso": False}

# Download e processar
def _baixar_e_processar_arquivo(resource: Dict, pasta_temp: str) -> Dict:
    """
    Baixa e processa um arquivo com suporte a CSV, XLSX e ZIP.
    
    Fluxo:
    1. Detecta tipo de arquivo (CSV, XLSX, ZIP)
    2. Verifica cache
    3. Baixa se necessário
    4. Processa conforme tipo
    5. Salva em cache
    
    Args:
        resource: Recurso da API
        pasta_temp: Pasta temporária para salvar arquivos
    
    Returns:
        Dict com sucesso/erro e dados do arquivo
    """
    url = resource.get("url")
    nome = resource.get("name", "arquivo_sem_nome")
    mimetype = resource.get("mimetype", "")
    
    chave = _gerar_chave_cache(url, nome)
    
    cache_info = _arquivo_existe_no_cache(chave)
    if cache_info:
        return {
            "df": cache_info["dataframe"],
            "nome": nome,
            "path": cache_info["path"],
            "tipo_arquivo": cache_info.get("tipo_arquivo", "desconhecido"),
            "do_cache": True,
            "sucesso": True
        }
    
    tipo_arquivo = _detectar_tipo_arquivo(nome, mimetype)
    logger.info(f"Baixando arquivo: {nome}")
    logger.info(f"Tipo detectado: {tipo_arquivo.upper()}")
    
    try:
        response = requests.get(url, timeout=TIMEOUT_REQUISICAO, stream=True)
        response.raise_for_status()
        conteudo = response.content
        tamanho_mb = len(conteudo) / (1024*1024)
        logger.info(f"Tamanho do arquivo: {tamanho_mb:.2f} MB")
        
    except requests.exceptions.Timeout:
        error_msg = f"Timeout ({TIMEOUT_REQUISICAO}s) ao baixar arquivo"
        logger.error(error_msg)
        return _criar_resposta_erro(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro de rede ao baixar: {e}"
        logger.error(error_msg)
        return _criar_resposta_erro(error_msg)
    
    if tipo_arquivo == "xlsx":
        logger.info("Processando arquivo como XLSX...")
        df = _processar_xlsx(conteudo)
    elif tipo_arquivo == "zip":
        logger.info("Processando arquivo como ZIP...")
        df = _processar_zip(conteudo)
    elif tipo_arquivo == "csv":
        logger.info("Processando arquivo como CSV...")
        df = _processar_csv(conteudo)
    else:
        logger.warning(f"Tipo desconhecido, tentando como CSV...")
        df = _processar_csv(conteudo)
    
    if not _validar_dataframe(df):
        error_msg = f"DataFrame vazio ou inválido após processamento de {tipo_arquivo.upper()}"
        logger.error(error_msg)
        return _criar_resposta_erro(error_msg)
    
    path = os.path.join(pasta_temp, nome)
    try:
        with open(path, 'wb') as f:
            f.write(conteudo)
        logger.info(f"Arquivo salvo localmente: {path}")
    except IOError as e:
        error_msg = f"Erro ao salvar arquivo: {e}"
        logger.error(error_msg)
        return _criar_resposta_erro(error_msg)

    logger.info(f"DataFrame processado: {len(df):,} linhas × {len(df.columns)} colunas")
    memoria_mb = df.memory_usage(deep=True).sum() / (1024*1024)
    logger.info(f"Memória utilizada: {memoria_mb:.2f} MB")
    
    info_cache = {
        "nome": nome,
        "path": path,
        "dataframe": df,
        "url_original": url,
        "tipo_arquivo": tipo_arquivo,
        "tamanho_mb": round(len(conteudo) / (1024*1024), 2),
        "linhas": len(df),
        "colunas": len(df.columns),
        "nomes_colunas": list(df.columns),
    }
    
    _salvar_cache(chave, info_cache)
    
    return {
        "df": df,
        "nome": nome,
        "path": path,
        "tipo_arquivo": tipo_arquivo,
        "do_cache": False,
        "sucesso": True
    }