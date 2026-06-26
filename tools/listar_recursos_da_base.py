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
        
        recursos_filtrados = []
        for r in resources:
            # Correspondência com termo (antigo _recurso_correspondente)
            if termo_busca:
                texto = f"{r.get('name', '')} {r.get('description', '')}".lower()
                if not all(t in texto for t in termo_busca.lower().split()):
                    continue
            
            # Formatação de tamanho (antigo _formatar_tamanho)
            size_bytes = r.get("size")
            if not size_bytes:
                size_fmt = "N/A"
            else:
                size_fmt = f"{size_bytes} B"
                for unidade, divisor in [('GB', 1024**3), ('MB', 1024**2), ('KB', 1024)]:
                    if size_bytes >= divisor:
                        size_fmt = f"{size_bytes/divisor:.1f} {unidade}"
                        break
            
            recursos_filtrados.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "description": r.get("description", ""),
                "format": r.get("format", "").upper(),
                "size": size_fmt,
                "url": r.get("url"),
                "created": r.get("created", "")[:10],
                "last_modified": r.get("last_modified", "")[:10]
            })
        
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
        
        # Truncamento da descrição (antigo _truncar)
        notes = package_info.get("notes", "")
        package_description = notes[:200] + "..." if len(notes) > 200 else notes
        
        return {
            "package_id": package_id,
            "package_title": package_info.get("title", ""),
            "package_description": package_description,
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
                "percentual": round((freq / len(nomes)) * 100, 1),
                "exemplo": exemplo
            })
    
    return resultados[:3]

def _detectar_estruturas(nomes: List[str]) -> List[Dict]:
    """Detecta padrões de estrutura de nomes"""
    estruturas = Counter()
    nome_para_template = {}
    
    # Conversão para template incorporada (antigo _converter_para_template)
    for nome in nomes:
        template = nome
        for chave, padrao in REGEX_PATTERNS.items():
            template = re.sub(padrao, REGEX_REPLACEMENTS[chave], template)
        template = re.sub(r'[_\-\s]+', '_', template).upper()
        nome_para_template[nome] = template
        estruturas[template] += 1
    
    resultados = []
    for estrutura, freq in estruturas.most_common(3):
        if freq > 1:
            exemplo = next((n for n in nomes if nome_para_template[n] == estrutura), "")
            resultados.append({
                "template": estrutura,
                "frequencia": freq,
                "percentual": round((freq / len(nomes)) * 100, 1),
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
                "percentual": round((freq / len(nomes)) * 100, 1),
                "exemplos": exemplos
            })
    
    return resultados