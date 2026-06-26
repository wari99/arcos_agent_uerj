import io
import zipfile
import pandas as pd
from typing import Optional

from tools.commons.settings import (
    AMOSTRA_DETECCAO,
    LIMIAR_SEPARADOR,
    ENCODING_PADRAO,
    SEPARADORES_CSV,
    ENCODINGS_SUPORTADOS,
)

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