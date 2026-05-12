import os
import io
import zipfile
import tempfile
import requests
import pandas as pd
import shutil
import hashlib
from typing import Any, Dict, Optional
from langchain.tools import tool

TIMEOUT_REQUISICAO = 60  # segundos
AMOSTRA_DETECCAO = 2000  # primeiros N bytes para detectar padrão
LIMIAR_SEPARADOR = 10    # mínimo de ocorrências para considerar válido
MAX_ARQUIVOS = 5         # máximo de arquivos a processar
ENCODING_PADRAO = 'utf-8'
ENCODINGS = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
SEPARADORES = [';', ',', '\t']

_pasta_temporaria_global = None
_cache_arquivos: Dict[str, Dict] = {}

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
        
        url = f"https://dadosabertos.rj.gov.br/api/3/action/package_show?id={package_id}"
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
            resources = [r for r in resources if file_filter.lower() in r.get("name", "").lower()]
        
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
    
# =============== FUNCOES AUXILIARES

def obter_pasta_temporaria() -> Optional[str]:
    """Retorna o caminho da pasta temporária atual"""
    return _pasta_temporaria_global

def obter_cache_arquivos() -> Dict:
    """Retorna o cache de arquivos para outras tools"""
    return _cache_arquivos

def listar_cache_arquivos() -> Dict:
    """Lista arquivos atualmente no cache"""
    arquivos_cache = []
    total_mb = 0
    
    for info in _cache_arquivos.values():
        if os.path.exists(info["arquivo_local"]):
            arquivos_cache.append({
                "nome": info["nome"],
                "linhas": info["linhas"],
                "colunas": info["colunas"],
                "tamanho_mb": info["tamanho_mb"],
                "arquivo_local": info["arquivo_local"]
            })
            total_mb += info["tamanho_mb"]
    
    return {
        "total_arquivos_cache": len(arquivos_cache),
        "total_tamanho_mb": round(total_mb, 2),
        "arquivos": arquivos_cache
    }

def limpar_pasta_temporaria_manual() -> Dict:
    """Limpa pasta temporária e cache"""
    global _pasta_temporaria_global, _cache_arquivos
    
    if not (_pasta_temporaria_global and os.path.exists(_pasta_temporaria_global)):
        return {"status": "info", "mensagem": "Nenhuma pasta temporária para remover"}
    
    try:
        shutil.rmtree(_pasta_temporaria_global)
        print(f"🗑️ Pasta removida: {_pasta_temporaria_global}")
        
        _pasta_temporaria_global = None
        _cache_arquivos.clear()
        print("🧹 Cache limpo")
        
        return {"status": "sucesso", "mensagem": "Pasta e cache removidos"}
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro ao remover: {e}"}

# =============== FUNCOES INTERNAS 

def _criar_pasta_temporaria() -> str:
    """Cria ou retorna pasta temporária existente"""
    global _pasta_temporaria_global
    
    if _pasta_temporaria_global is None or not os.path.exists(_pasta_temporaria_global):
        _pasta_temporaria_global = tempfile.mkdtemp(prefix="arcos_rj_")
        print(f"📂 Pasta criada: {_pasta_temporaria_global}")
    
    return _pasta_temporaria_global

def _gerar_chave_cache(url: str, nome: str) -> str:
    """Gera chave única para cache"""
    conteudo = f"{url}|{nome}"
    return hashlib.md5(conteudo.encode()).hexdigest()[:16]

def _detectar_encoding(conteudo_bytes: bytes) -> str:
    """Detecta encoding do arquivo testando sequencialmente"""
    for encoding in ENCODINGS:
        try:
            conteudo_bytes.decode(encoding)
            if encoding != ENCODING_PADRAO:
                print(f"🔄 Encoding detectado: {encoding}")
            return encoding
        except UnicodeDecodeError:
            continue
    
    print("⚠️ Usando UTF-8 com substituição de caracteres")
    return ENCODING_PADRAO

def _detectar_separador(amostra: str) -> str:
    """Detecta melhor separador para CSV"""
    contadores = {sep: amostra.count(sep) for sep in SEPARADORES}
    
    separador_melhor = max(contadores, key=contadores.get)
    
    if contadores[separador_melhor] < LIMIAR_SEPARADOR:
        separador_melhor = ';'  
    
    if separador_melhor == ';':
        print("🇧🇷 Separador: ponto-e-vírgula")
    elif separador_melhor == ',':
        print("🌍 Separador: vírgula")
    else:
        print("📊 Separador: tabulação")
    
    return separador_melhor

def _ler_csv(conteudo: str) -> Optional[pd.DataFrame]:
    """Lê CSV com detecção automática de separador"""
    try:
        separador = _detectar_separador(conteudo[:AMOSTRA_DETECCAO])
        return pd.read_csv(io.StringIO(conteudo), sep=separador)
    except Exception as e:
        print(f"❌ Erro ao ler CSV com '{separador}': {e}")
        return None

# ================ CACHE

def _arquivo_existe_no_cache(chave: str) -> Optional[Dict]:
    """Verifica se arquivo já foi baixado e ainda existe"""
    if chave not in _cache_arquivos:
        return None
    
    info = _cache_arquivos[chave]
    
    if not os.path.exists(info.get("arquivo_local", "")):
        del _cache_arquivos[chave]
        return None
    
    print(f"♻️ Cache: {info['nome']}")
    return info

def _salvar_cache(chave: str, info: Dict) -> None:
    """Salva arquivo no cache"""
    _cache_arquivos[chave] = info
    print(f"💾 Cache: {info['nome']}")

def _validar_dataframe(df: Optional[pd.DataFrame]) -> bool:
    """Valida se DataFrame é válido"""
    return df is not None and not df.empty

def _criar_resposta_erro(mensagem: str) -> Dict:
    """Cria resposta padronizada de erro"""
    return {"erro": mensagem, "sucesso": False}

# =============== PROCESSAMENTO ARQUIVOS

def _processar_zip(conteudo_bytes: bytes) -> Optional[pd.DataFrame]:
    """Extrai e processa CSV de ZIP"""
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo_bytes)) as zip_ref:
            csvs = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]
            
            if not csvs:
                print("❌ ZIP não contém CSV")
                return None
            
            arquivo_csv = csvs[0]
            print(f"📄 Extraindo: {arquivo_csv}")
            
            with zip_ref.open(arquivo_csv) as f:
                encoding = _detectar_encoding(f.read()[:AMOSTRA_DETECCAO])
                f.seek(0)
                conteudo = f.read().decode(encoding, errors='replace')
                return _ler_csv(conteudo)
                
    except zipfile.BadZipFile:
        print("❌ ZIP corrompido")
        return None
    except Exception as e:
        print(f"❌ Erro ao processar ZIP: {e}")
        return None

def _processar_csv(conteudo_bytes: bytes) -> Optional[pd.DataFrame]:
    """Processa arquivo CSV direto"""
    try:
        encoding = _detectar_encoding(conteudo_bytes[:AMOSTRA_DETECCAO])
        conteudo = conteudo_bytes.decode(encoding, errors='replace')
        return _ler_csv(conteudo)
    except Exception as e:
        print(f"❌ Erro ao processar CSV: {e}")
        return None

def _baixar_e_processar_arquivo(resource: Dict, pasta_temp: str) -> Dict:
    """Baixa e processa um arquivo com cache automático"""
    url = resource.get("url")
    nome = resource.get("name", "arquivo_sem_nome")
    mimetype = (resource.get("mimetype") or "").lower()
    
    chave = _gerar_chave_cache(url, nome)
    cache_info = _arquivo_existe_no_cache(chave)
    
    if cache_info:
        return {
            "df": cache_info["dataframe"],
            "nome": nome,
            "arquivo_local": cache_info["arquivo_local"],
            "do_cache": True,
            "sucesso": True
        }
    
    print(f"\n⬇️ Baixando: {nome}")
    try:
        response = requests.get(url, timeout=TIMEOUT_REQUISICAO, stream=True)
        response.raise_for_status()
        conteudo = response.content
        
    except requests.exceptions.Timeout:
        return _criar_resposta_erro(f"Timeout ({TIMEOUT_REQUISICAO}s)")
    except requests.exceptions.RequestException as e:
        return _criar_resposta_erro(f"Erro de rede: {e}")
    
    is_zip = "zip" in mimetype or nome.lower().endswith(".zip")
    df = _processar_zip(conteudo) if is_zip else _processar_csv(conteudo)
    
    if not _validar_dataframe(df):
        return _criar_resposta_erro("DataFrame vazio ou inválido")
    
    arquivo_local = os.path.join(pasta_temp, nome)
    try:
        with open(arquivo_local, 'wb') as f:
            f.write(conteudo)
    except IOError as e:
        return _criar_resposta_erro(f"Erro ao salvar arquivo: {e}")
    
    print(f"✅ {len(df)} linhas, {len(df.columns)} colunas")
    
    info_cache = {
        "nome": nome,
        "arquivo_local": arquivo_local,
        "dataframe": df,
        "url_original": url,
        "tamanho_mb": round(len(conteudo) / (1024*1024), 2),
        "linhas": len(df),
        "colunas": len(df.columns)
    }
    
    _salvar_cache(chave, info_cache)
    
    return {
        "df": df,
        "nome": nome,
        "arquivo_local": arquivo_local,
        "do_cache": False,
        "sucesso": True
    }
