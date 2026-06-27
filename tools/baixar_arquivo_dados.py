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

from tools.commons.settings import (
    TIMEOUT_REQUISICAO,
    MAX_ARQUIVOS,
    REGEX_PATTERNS
)
from tools.commons.utils import (
    _processar_xlsx,
    _processar_csv,
    _processar_zip,
    _estado
)

load_dotenv()

# =============== TOOL FUNCTIONS

@tool("baixar_arquivo_dados")
def baixar_arquivo_dados(params: dict) -> Any:
    """Baixa e processa arquivos de uma base de dados"""
    
    try:
        package_id = params.get("package_id", "").strip()
        file_filter = params.get("file_filter", "").strip()
        
        if not package_id:
            return _criar_resposta_erro("Parâmetro 'package_id' obrigatório")
        
        print(f"🔍 Base: '{package_id}' | Filtro: '{file_filter}'")
        
        url = os.getenv("URL_CONSULTAR_PROCESSAR_ARQUIVO").format(package_id)

        try:
            resp = requests.get(url, timeout=TIMEOUT_REQUISICAO)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return _criar_resposta_erro(f"Erro ao buscar API: {e}")
        
        if not data.get("success"):
            return _criar_resposta_erro("Pacote não encontrado ou inacessível")
        
        resources = data["result"].get("resources", [])
        
        if not resources:
            return _criar_resposta_erro("Nenhum recurso encontrado")
        
        if file_filter:
            resources = _filtro_deteccao_padrao_estrutural(resources, file_filter)
        
        if not resources:
            return _criar_resposta_erro(f"Nenhum arquivo com filtro: '{file_filter}'")
        
        resources = resources[:MAX_ARQUIVOS]
        print(f"📁 {len(resources)} arquivo(s)")
        
        pasta_temp = _criar_pasta_temporaria()
        resultados = {}
        stats = {"sucesso": 0, "erro": 0, "cache": 0, "novos": 0}
        
        for resource in resources:
            resultado = _baixar_e_processar_arquivo(resource, pasta_temp)
            nome = resource.get("name", "arquivo")
            
            if not resultado.get("sucesso"):
                resultados[nome] = resultado
                stats["erro"] += 1
                continue
            
            df = resultado["df"]
            memoria_mb = df.memory_usage(deep=True).sum() / (1024*1024)
            
            resultados[nome] = {
                "linhas": len(df),
                "colunas": len(df.columns),
                "nomes_colunas": list(df.columns),
                "memoria_mb": round(memoria_mb, 2),
                "arquivo_local": resultado["arquivo_local"],
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
        
        return resultados
        
    except Exception as e:
        return _criar_resposta_erro(f"Erro geral: {e}")

# =============== FUNCOES INTERNAS DETECTAR TIPO

def _detectar_tipo_arquivo(nome: str, mimetype: str) -> str:
    """
    Detecta tipo de arquivo com prioridade correta
    """
    nome_lower = nome.lower()
    mime_lower = (mimetype or "").lower()
    
    print(f"   🔍 Detecção: nome='{nome_lower}' | mime='{mime_lower}'")
    
    if nome_lower.endswith(".xlsx"):
        print(f"   ✅ Detectado: XLSX (por extensão)")
        return "xlsx"
    
    if "spreadsheet" in mime_lower or "ms-excel" in mime_lower:
        print(f"   ✅ Detectado: XLSX (por MIME type)")
        return "xlsx"
    
    if "openxmlformats" in mime_lower or "officedocument" in mime_lower:
        print(f"   ✅ Detectado: XLSX (por MIME OpenXML)")
        return "xlsx"
    
    if nome_lower.endswith(".zip"):
        print(f"   ✅ Detectado: ZIP (por extensão)")
        return "zip"
    
    if "zip" in mime_lower:
        print(f"   ✅ Detectado: ZIP (por MIME type)")
        return "zip"
    
    if nome_lower.endswith(".csv"):
        print(f"   ✅ Detectado: CSV (por extensão)")
        return "csv"
    
    if "csv" in mime_lower or "text/plain" in mime_lower:
        print(f"   ✅ Detectado: CSV (por MIME type)")
        return "csv"
    
    if nome_lower.endswith(".pdf") or "pdf" in mime_lower:
        print(f"   ⚠️ Tipo: PDF (não suportado)")
        return "pdf"
    
    print(f"   ⚠️ Tipo desconhecido: {nome_lower}")
    return "desconhecido"

# =============== FUNCOES INTERNAS - CRIAR PASTA E CACHE

def _criar_pasta_temporaria() -> str:
    """Cria ou retorna pasta temporária existente"""
    if _estado.pasta_temporaria_global is None or not os.path.exists(_estado.pasta_temporaria_global):
        _estado.pasta_temporaria_global = tempfile.mkdtemp(prefix="arcos_rj_")

        print(f"📂 Pasta criada: {_estado.pasta_temporaria_global}")

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

    if not os.path.exists(info.get("arquivo_local", "")):
        del _estado.cache_arquivos[chave]
        return None

    print(f"♻️ Cache: {info['nome']}")
    return info

def _salvar_cache(chave: str, info: Dict) -> None:
    """Salva arquivo no cache"""
    _estado.cache_arquivos[chave] = info
    print(f"💾 Cache: {info['nome']}")

def _validar_dataframe(df: Optional[pd.DataFrame]) -> bool:
    """Valida se DataFrame é válido"""
    return df is not None and not df.empty

def _criar_resposta_erro(mensagem: str) -> Dict:
    """Cria resposta padronizada de erro"""
    return {"erro": mensagem, "sucesso": False}

# =============== FUNCAO PRINCIPAL - DOWNLOAD E PROCESSAMENTO

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
            "arquivo_local": cache_info["arquivo_local"],
            "tipo_arquivo": cache_info.get("tipo_arquivo", "desconhecido"),
            "do_cache": True,
            "sucesso": True
        }
    
    tipo_arquivo = _detectar_tipo_arquivo(nome, mimetype)
    print(f"\n⬇️ Baixando: {nome}")
    print(f"   Tipo detectado: {tipo_arquivo.upper()}")
    
    try:
        response = requests.get(url, timeout=TIMEOUT_REQUISICAO, stream=True)
        response.raise_for_status()
        conteudo = response.content
        tamanho_mb = len(conteudo) / (1024*1024)
        print(f"   Tamanho: {tamanho_mb:.2f} MB")
        
    except requests.exceptions.Timeout:
        return _criar_resposta_erro(f"Timeout ({TIMEOUT_REQUISICAO}s) ao baixar arquivo")
    except requests.exceptions.RequestException as e:
        return _criar_resposta_erro(f"Erro de rede ao baixar: {e}")
    
    if tipo_arquivo == "xlsx":
        print("📊 Processando como XLSX...")
        df = _processar_xlsx(conteudo)
    elif tipo_arquivo == "zip":
        print("📦 Processando como ZIP...")
        df = _processar_zip(conteudo)
    elif tipo_arquivo == "csv":
        print("📄 Processando como CSV...")
        df = _processar_csv(conteudo)
    else:
        print(f"⚠️ Tipo desconhecido, tentando como CSV...")
        df = _processar_csv(conteudo)
    
    if not _validar_dataframe(df):
        return _criar_resposta_erro(
            f"DataFrame vazio ou inválido após processamento de {tipo_arquivo.upper()}"
        )
    
    arquivo_local = os.path.join(pasta_temp, nome)
    try:
        with open(arquivo_local, 'wb') as f:
            f.write(conteudo)
        print(f"✅ Arquivo salvo: {arquivo_local}")
    except IOError as e:
        return _criar_resposta_erro(f"Erro ao salvar arquivo: {e}")

    print(f"✅ {len(df):,} linhas × {len(df.columns)} colunas")
    memoria_mb = df.memory_usage(deep=True).sum() / (1024*1024)
    print(f"   Memória: {memoria_mb:.2f} MB")
    
    info_cache = {
        "nome": nome,
        "arquivo_local": arquivo_local,
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
        "arquivo_local": arquivo_local,
        "tipo_arquivo": tipo_arquivo,
        "do_cache": False,
        "sucesso": True
    }


def _filtro_deteccao_padrao_estrutural(recursos: list, file_filter: str) -> list:
    """
    Filtra recursos por detecção de padrão estrutural.
    
    - YYYY_MM (sem dia) → prioriza arquivos que NÃO têm YYYY_MM_DD no nome
    - YYYY_MM_DD (com dia) → busca apenas arquivos com aquele dia
    - Outros → busca genérica (contains)
    """
    if not file_filter or not file_filter.strip():
        return recursos
    
    filtro_lower = file_filter.lower().strip()
    match_data = re.search(REGEX_PATTERNS['data_filtro'], filtro_lower)
    
    # REGRA 1: Data completa YYYY_MM_DD → arquivo daquele dia 
    if match_data and match_data.group(4):
        data_str = f"{match_data.group(1)}_{match_data.group(2)}_{match_data.group(4)}"
        resultado = [
            r for r in recursos
            if data_str in r.get("name", "")
        ]
        print(f"   🎯 Padrão: dia {data_str} → {len(resultado)} arquivo(s)")
        return resultado
    
    # REGRA 2: Apenas mês YYYY_MM -> prioriza arquivos SEM dia no nome 
    if match_data and not match_data.group(4):
        data_str = f"{match_data.group(1)}_{match_data.group(2)}"
        
        # Separar: arquivos que TÊM o mês mas NÃO têm dia (padrão mensal/consolidado)
        mensais = [
            r for r in recursos
            if data_str in r.get("name", "")
            and not re.search(REGEX_PATTERNS['data_completa_nome'], r.get("name", ""))
        ]
        
        # Arquivos que TÊM o mês E têm dia (padrão diário)
        diarios = [
            r for r in recursos
            if data_str in r.get("name", "")
            and re.search(REGEX_PATTERNS['data_completa_nome'], r.get("name", ""))
        ]
        
        if mensais:
            print(f"   🎯 Padrão: mês {data_str} → {len(mensais)} arquivo(s) mensal(is)")
            return mensais
        
        print(f"   ⚠️ Padrão: mês {data_str} → sem mensal, usando {len(diarios)} diário(s)")
        return diarios
    
    # REGRA 3: Busca genérica 
    resultado = [r for r in recursos if filtro_lower in r.get("name", "").lower()]
    print(f"   🔍 Filtro genérico '{filtro_lower}' → {len(resultado)} arquivo(s)")
    return resultado