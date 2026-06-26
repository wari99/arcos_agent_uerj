import requests
import re
import os
from typing import Any, List, Optional, Dict
from collections import Counter
from langchain.tools import tool
from dotenv import load_dotenv
from tools.commons.settings import LIMIARES_DETECCAO, REGEX_PATTERNS, REGEX_REPLACEMENTS

load_dotenv()

# ================= TOOL FUNCTIONS

@tool("listar_recursos_da_base")
def listar_recursos_da_base(
    package_id: str,
    termo_busca: Optional[str] = None,
    limite: int = 10,
    analisar_padroes: bool = True
) -> Any:
    """Lista recursos de uma base com análise de padrões"""
    
    try:
        url = os.getenv("URL_CONSULTAR_PROCESSAR_ARQUIVO").format(package_id)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        if not data.get("success"):
            return {"erro": "Package não encontrado", "sucesso": False}
        
        package_info = data["result"]
        resources = package_info.get("resources", [])
        
        if not resources:
            return {
                "package_id": package_id,
                "package_title": package_info.get("title", ""),
                "total_recursos": 0,
                "recursos": [],
                "sucesso": False
            }
        
        recursos_filtrados = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "description": r.get("description", ""),
                "format": r.get("format", "").upper(),
                "size": _formatar_tamanho(r.get("size")),
                "url": r.get("url"),
                "created": r.get("created", "")[:10],
                "last_modified": r.get("last_modified", "")[:10]
            }
            for r in resources
            if _recurso_correspondente(r, termo_busca)
        ]
        
        recursos_limitados = recursos_filtrados[:limite]
        
        padroes_info = {}
        if analisar_padroes and recursos_filtrados:
            nomes = [r.get("name", "") for r in resources]
            padroes_info = {
                "prefixos": _detectar_prefixos(nomes),
                "estruturas": _detectar_estruturas(nomes),
                "padroes_numericos": _detectar_padroes_numericos(nomes),
                "palavras_frequentes": _detectar_palavras(nomes)
            }
        
        return {
            "package_id": package_id,
            "package_title": package_info.get("title", ""),
            "package_description": _truncar(package_info.get("notes", "")),
            "total_recursos_na_base": len(resources),
            "recursos_encontrados": len(recursos_filtrados),
            "recursos_retornados": len(recursos_limitados),
            "recursos": recursos_limitados,
            "padroes": padroes_info if analisar_padroes else None,
            "sucesso": True
        }
        
    except requests.exceptions.Timeout:
        return {"erro": "Timeout na requisição", "sucesso": False}
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro de rede: {e}", "sucesso": False}
    except Exception as e:
        return {"erro": f"Erro: {e}", "sucesso": False}
    
# ================= DETECCAO PADRAO

def _detectar_prefixos(nomes: List[str]) -> List[Dict]:
    """Detecta prefixos comuns"""
    if len(nomes) < 2:
        return []
    
    prefixos = Counter()
    separadores = ['_', '-', '.', ' ']
    
    for nome in nomes:
        for sep in separadores:
            if sep in nome:
                partes = nome.split(sep)
                if len(partes) >= 2 and len(partes[0]) > 1:
                    prefixos[partes[0].upper()] += 1
                if len(partes) >= 3 and len(partes[0]) > 1 and len(partes[1]) > 1:
                    prefixos[f"{partes[0]}{sep}{partes[1]}".upper()] += 1
    
    resultados = []
    limiar = len(nomes) * LIMIARES_DETECCAO['prefixo_separador']
    
    for prefixo, freq in prefixos.most_common(5):
        if freq > limiar:
            exemplo = next((n for n in nomes if prefixo in n.upper()), "")
            resultados.append({
                "prefixo": prefixo,
                "frequencia": freq,
                "percentual": _percentual(freq, len(nomes)),
                "exemplo": exemplo
            })
    
    return resultados[:3]

def _detectar_estruturas(nomes: List[str]) -> List[Dict]:
    """Detecta padrões de estrutura de nomes"""
    estruturas = Counter()
    
    for nome in nomes:
        template = _converter_para_template(nome)
        estruturas[template] += 1
    
    resultados = []
    for estrutura, freq in estruturas.most_common(3):
        if freq > 1:
            exemplo = next((n for n in nomes if _converter_para_template(n) == estrutura), "")
            resultados.append({
                "template": estrutura,
                "frequencia": freq,
                "percentual": _percentual(freq, len(nomes)),
                "exemplo": exemplo
            })
    
    return resultados

def _detectar_padroes_numericos(nomes: List[str]) -> Dict:
    """Detecta anos, datas e sequências"""
    anos_detectados = set()
    sequencias = set()
    
    for nome in nomes:
        anos_detectados.update(re.findall(r'\b(19\d{2}|20\d{2}|21\d{2})\b', nome))
        sequencias.update([int(s) for s in re.findall(r'\b(0\d|[1-9]\d?)\b', nome)])
    
    resultado = {}
    
    if anos_detectados:
        anos_sorted = sorted(anos_detectados)
        resultado["anos"] = {
            "lista": anos_sorted,
            "range": f"{anos_sorted[0]}-{anos_sorted[-1]}"
        }
    
    if len(sequencias) > LIMIARES_DETECCAO['min_sequencias']:
        seq_sorted = sorted(sequencias)
        resultado["sequencias"] = {
            "range": f"{seq_sorted[0]:02d}-{seq_sorted[-1]:02d}",
            "pode_ser_mes": max(sequencias) <= 12,
            "pode_ser_dia": max(sequencias) <= 31
        }
    
    return resultado

def _detectar_palavras(nomes: List[str]) -> List[Dict]:
    """Detecta palavras frequentes"""
    palavras = Counter()
    
    for nome in nomes:
        nome_sem_ext = nome.split('.')[0] if '.' in nome else nome
        tokens = re.split(r'[_\-\s\.]+', nome_sem_ext.upper())
        palavras.update([t for t in tokens if len(t) > 2 and not t.isdigit()])
    
    resultados = []
    for palavra, freq in palavras.most_common(10):
        if freq > LIMIARES_DETECCAO['min_frequencia']:
            exemplos = [n for n in nomes if palavra in n.upper()][:2]
            resultados.append({
                "palavra": palavra,
                "frequencia": freq,
                "percentual": _percentual(freq, len(nomes)),
                "exemplos": exemplos
            })
    
    return resultados

# ================= AUXILIARES

def _truncar(texto: str, limite: int = 200) -> str:
    """Trunca texto se exceder limite"""
    return texto[:limite] + "..." if len(texto) > limite else texto

def _percentual(freq: int, total: int) -> float:
    """Calcula percentual"""
    return round((freq / total) * 100, 1) if total > 0 else 0

def _converter_para_template(nome: str) -> str:
    """Converte nome em template genérico"""
    template = nome
    for chave, padrao in REGEX_PATTERNS.items():
        template = re.sub(padrao, REGEX_REPLACEMENTS[chave], template)
    template = re.sub(r'[_\-\s]+', '_', template)
    return template.upper()

def _recurso_correspondente(recurso: Dict, termo: str) -> bool:
    """Verifica se recurso corresponde ao termo de busca"""
    if not termo:
        return True
    texto = f"{recurso.get('name', '')} {recurso.get('description', '')}".lower()
    return all(t in texto for t in termo.lower().split())

def _formatar_tamanho(size_bytes: int) -> str:
    """Converte bytes para formato legível"""
    if not size_bytes:
        return "N/A"
    for unidade, divisor in [('GB', 1024**3), ('MB', 1024**2), ('KB', 1024)]:
        if size_bytes >= divisor:
            return f"{size_bytes/divisor:.1f} {unidade}"
    return f"{size_bytes} B"
