import os
import shutil
import io
import tempfile
import zipfile
import re
import pandas as pd
from typing import Optional, Dict

from tools.commons.settings import (
    AMOSTRA_DETECCAO,
    LIMIAR_SEPARADOR,
    ENCODING_PADRAO,
    SEPARADORES_CSV,
    ENCODINGS_SUPORTADOS,
    REGEX_PATTERNS,
)

# =============== GERENCIAMENTO CACHE

class _EstadoCache:
    """
    Centraliza o estado que antes eram as variáveis globais
    `_pasta_temporaria_global` e `_cache_arquivos`.
    Como é um único objeto compartilhado, mutações são vistas por todos os módulos.
    """
    def __init__(self):
        self.pasta_temporaria_global: Optional[str] = None
        self.cache_arquivos: Dict[str, Dict] = {}

_estado = _EstadoCache()

def obter_pasta_temporaria() -> Optional[str]:
    """Retorna o caminho da pasta temporária atual"""
    return _estado.pasta_temporaria_global


def obter_cache_arquivos() -> Dict:
    """Retorna o cache de arquivos para outras tools"""
    return _estado.cache_arquivos


def listar_cache_arquivos() -> Dict:
    """Lista arquivos atualmente no cache"""
    arquivos_cache = []
    total_mb = 0

    for info in _estado.cache_arquivos.values():
        if os.path.exists(info["arquivo_local"]):
            arquivos_cache.append({
                "nome": info["nome"],
                "linhas": info["linhas"],
                "colunas": info["colunas"],
                "tamanho_mb": info["tamanho_mb"],
                "tipo_arquivo": info.get("tipo_arquivo", "desconhecido"),
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
    print(f"🔍 DEBUG: _pasta_temporaria_global = {_estado.pasta_temporaria_global}")
    print(f"🔍 DEBUG: Existe? {os.path.exists(_estado.pasta_temporaria_global) if _estado.pasta_temporaria_global else False}")

    if not (_estado.pasta_temporaria_global and os.path.exists(_estado.pasta_temporaria_global)):
        print("📭 Sem pasta para limpar")
        return {"status": "info", "mensagem": "Nenhuma pasta temporária para remover"}

    try:
        print(f"🗑️ Removendo: {_estado.pasta_temporaria_global}")
        shutil.rmtree(_estado.pasta_temporaria_global)
        print(f"✅ Pasta removida: {_estado.pasta_temporaria_global}")

        _estado.pasta_temporaria_global = None
        _estado.cache_arquivos.clear()
        print("🧹 Cache limpo")

        return {"status": "sucesso", "mensagem": "Pasta e cache removidos"}
    except Exception as e:
        print(f"❌ Erro: {e}")
        return {"status": "erro", "mensagem": f"Erro ao remover: {e}"}

# =============== GERENCIAMENTO CACHE

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

# =============== FUNCOES INTERNAS - ENCODING

def _detectar_encoding(conteudo_bytes: bytes) -> str:
    """Detecta encoding do arquivo testando sequencialmente"""
    for encoding in ENCODINGS_SUPORTADOS:
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
    contadores = {sep: amostra.count(sep) for sep in SEPARADORES_CSV}
    
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

# =============== FUNCOES INTERNAS - PROCESSAR ARQUIVOS

def _processar_xlsx(conteudo_bytes: bytes) -> Optional[pd.DataFrame]:
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
        
        df = pd.read_excel(
            arquivo_bytes,
            sheet_name=0,  
            engine='openpyxl',
            header=0  
        )
        
        print(f"✅ XLSX processado: {len(df)} linhas, {len(df.columns)} colunas")
        print(f"   Colunas: {list(df.columns)[:5]}..." if len(df.columns) > 5 else f"   Colunas: {list(df.columns)}")
        
        if df.empty:
            print("⚠️ XLSX está vazio (sem dados)")
            return None
        
        df = df.dropna(axis=1, how='all')
        df = df.dropna(axis=0, how='all')
        
        if df.empty:
            print("❌ XLSX não contém dados válidos após limpeza")
            return None
        
        print(f"✅ Após limpeza: {len(df)} linhas, {len(df.columns)} colunas")
        return df
        
    except Exception as e:
        print(f"❌ Erro ao processar XLSX: {e}")
        import traceback
        traceback.print_exc()
        return None


def _processar_csv(conteudo_bytes: bytes) -> Optional[pd.DataFrame]:
    """Processa arquivo CSV com detecção de encoding e separador"""
    try:
        encoding = _detectar_encoding(conteudo_bytes)
        amostra = conteudo_bytes[:10000].decode(encoding, errors='ignore')
        separador = _detectar_separador(amostra)
        
        print(f"   🔄 Encoding detectado: {encoding}")
        print(f"   🇧🇷 Separador: {separador}")
        
        df = pd.read_csv(
            io.BytesIO(conteudo_bytes),
            encoding=encoding,
            sep=separador,
            on_bad_lines='skip',  
            engine='python'      
        )
        
        return df if df is not None and not df.empty else None
        
    except Exception as e:
        print(f"   ❌ Erro ao processar CSV: {str(e)}")
        return None


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
                
                separador = _detectar_separador(conteudo[:AMOSTRA_DETECCAO])
                return pd.read_csv(io.StringIO(conteudo), sep=separador)
                
    except zipfile.BadZipFile:
        print("❌ ZIP corrompido")
        return None
    except Exception as e:
        print(f"❌ Erro ao processar ZIP: {e}")
        return None