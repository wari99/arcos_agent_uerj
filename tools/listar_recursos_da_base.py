import requests
from typing import Any, List, Optional, Dict
from langchain.tools import tool
import re
from collections import Counter

@tool("listar_recursos_da_base")
def listar_recursos_da_base(
    package_id: str,
    termo_busca: Optional[str] = None,
    limite: int = 10,
    analisar_padroes: bool = True
) -> Any:
    """
    Lista os recursos (arquivos) de uma base específica do portal Dados Abertos RJ
    com análise automática de padrões de nomes.
    
    Parâmetros:
    - package_id (str): ID do pacote/base (ex: 'setram_sgr')
    - termo_busca (str, opcional): termo para filtrar arquivos por nome
    - limite (int): máximo de recursos a retornar (default=10)
    - analisar_padroes (bool): se deve analisar padrões de nomes (default=True)
    """
    
    try:
        url = f"https://dadosabertos.rj.gov.br/api/3/action/package_show?id={package_id}"
        resp = requests.get(url, timeout=30)
        
        if resp.status_code != 200:
            return {"erro": f"Falha na requisição: HTTP {resp.status_code}"}
        
        data = resp.json()
        
        if not data.get("success"):
            return {"erro": "Package não encontrado ou inacessível"}
        
        package_info = data["result"]
        resources = package_info.get("resources", [])
        
        if not resources:
            return {
                "package_id": package_id,
                "package_title": package_info.get("title", ""),
                "total_recursos": 0,
                "recursos": [],
                "mensagem": "Nenhum recurso encontrado nesta base"
            }
        
        padroes_identificados = []
        sugestoes_busca = []
        
        if analisar_padroes:
            padroes_info = _analisar_padroes_nomes(resources)
            padroes_identificados = padroes_info["padroes"]
            sugestoes_busca = padroes_info["sugestoes"]
        
        recursos_filtrados = []
        
        for resource in resources:
            nome_arquivo = resource.get("name", "").lower()
            descricao = resource.get("description", "").lower()
            
            if not termo_busca:
                incluir = True
            else:
                termos = termo_busca.lower().split()
                incluir = all(
                    any(termo in campo for campo in [nome_arquivo, descricao])
                    for termo in termos
                )
            
            if incluir:
                recurso_info = {
                    "id": resource.get("id"),
                    "name": resource.get("name"),
                    "description": resource.get("description", ""),
                    "format": resource.get("format", "").upper(),
                    "mimetype": resource.get("mimetype", ""),
                    "size": _formatar_tamanho(resource.get("size")),
                    "url": resource.get("url"),
                    "created": resource.get("created", "")[:10], 
                    "last_modified": resource.get("last_modified", "")[:10]
                }
                recursos_filtrados.append(recurso_info)
        
        recursos_limitados = recursos_filtrados[:limite]
        
        resultado = {
            "package_id": package_id,
            "package_title": package_info.get("title", ""),
            "package_description": package_info.get("notes", "")[:200] + "..." if len(package_info.get("notes", "")) > 200 else package_info.get("notes", ""),
            "total_recursos_na_base": len(resources),
            "recursos_encontrados": len(recursos_filtrados),
            "recursos_retornados": len(recursos_limitados),
            "termo_busca_usado": termo_busca,
            "recursos": recursos_limitados
        }
        
        if analisar_padroes and padroes_identificados:
            resultado["padroes_identificados"] = padroes_identificados
            resultado["sugestoes_para_busca"] = sugestoes_busca
            resultado["dica_de_uso"] = "Use os padrões identificados para buscar arquivos específicos. Ex: 'TRANSACAO_GRATUIDADE 2025 01' para janeiro de 2025."
        
        if len(recursos_filtrados) > limite:
            resultado["observacao"] = f"Mostrando {len(recursos_limitados)} de {len(recursos_filtrados)} recursos encontrados"
        
        return resultado
        
    except requests.exceptions.Timeout:
        return {"erro": "Timeout na requisição. Tente novamente."}
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro de conexão: {str(e)}"}
    except Exception as e:
        return {"erro": f"Erro inesperado: {str(e)}"}


def _analisar_padroes_nomes(resources: List[Dict]) -> Dict:
    """
    ANÁLISE DINÂMICA: Detectando padrões automaticamente sem ficar usando hardcoding
    """
    nomes = [r.get("name", "") for r in resources if r.get("name")]
    
    if not nomes:
        return {"padroes": [], "sugestoes": []}
    
    print(f"🔍 Analisando {len(nomes)} arquivos dinamicamente...")
    
    padroes = []
    sugestoes = []
    
    extensoes = Counter()
    for nome in nomes:
        if '.' in nome:
            ext = nome.split('.')[-1].upper()
            extensoes[ext] += 1
    
    prefixos_dinamicos = _detectar_prefixos_dinamicos(nomes)
    estruturas_dinamicas = _detectar_estruturas_dinamicas(nomes)
    padroes_numericos = _detectar_padroes_numericos(nomes)
    palavras_comuns = _detectar_palavras_comuns(nomes)
    
    if extensoes.most_common(1):
        ext_principal = extensoes.most_common(1)[0]
        padroes.append({
            "tipo": "extensoes",
            "principal": ext_principal[0],
            "frequencia": ext_principal[1],
            "todas": dict(extensoes.most_common())
        })
    
    if prefixos_dinamicos:
        padroes.append({
            "tipo": "prefixos_detectados",
            "padroes": prefixos_dinamicos
        })
    
    if estruturas_dinamicas:
        padroes.append({
            "tipo": "estruturas_detectadas", 
            "estruturas": estruturas_dinamicas
        })
    
    if padroes_numericos:
        padroes.append({
            "tipo": "padroes_numericos",
            "padroes": padroes_numericos
        })
    
    if palavras_comuns:
        padroes.append({
            "tipo": "palavras_frequentes",
            "palavras": palavras_comuns
        })
    
    sugestoes = _gerar_sugestoes_dinamicas(nomes, prefixos_dinamicos, padroes_numericos, palavras_comuns)
    
    return {
        "padroes": padroes,
        "sugestoes": sugestoes
    }


def _detectar_prefixos_dinamicos(nomes: List[str]) -> List[Dict]:
    """
    🔍 Detecta prefixos comuns de forma completamente dinâmica
    """
    if len(nomes) < 2:
        return []
    
    resultados = []
    
    substring_inicial = _encontrar_prefixo_comum_real(nomes)
    if substring_inicial and len(substring_inicial) > 2:
        freq = sum(1 for nome in nomes if nome.upper().startswith(substring_inicial.upper()))
        if freq > len(nomes) * 0.3: 
            resultados.append({
                "prefixo": substring_inicial,
                "tipo": "substring_comum",
                "frequencia": freq,
                "percentual": round((freq/len(nomes))*100, 1),
                "exemplo": next(nome for nome in nomes if nome.upper().startswith(substring_inicial.upper()))
            })
    
    separadores = ['_', '-', '.', ' ']
    prefixos_por_separador = Counter()
    
    for nome in nomes:
        for sep in separadores:
            if sep in nome:
                partes = nome.split(sep)
                if len(partes) >= 2 and len(partes[0]) > 1:
                    prefixos_por_separador[partes[0].upper()] += 1
                if len(partes) >= 3 and len(partes[0]) > 1 and len(partes[1]) > 1:
                    prefixo_duplo = f"{partes[0]}{sep}{partes[1]}".upper()
                    prefixos_por_separador[prefixo_duplo] += 1
    
    for prefixo, freq in prefixos_por_separador.most_common(5):
        if freq > 1 and freq > len(nomes) * 0.15:  
            percentual = round((freq/len(nomes))*100, 1)
            exemplo = next((nome for nome in nomes if prefixo in nome.upper()), "")
            
            resultados.append({
                "prefixo": prefixo,
                "tipo": "por_separador", 
                "frequencia": freq,
                "percentual": percentual,
                "exemplo": exemplo
            })
    
    return _filtrar_prefixos_similares(resultados)


def _encontrar_prefixo_comum_real(nomes: List[str]) -> str:
    """
    🔍 Encontra o prefixo comum real no início dos nomes
    """
    if not nomes:
        return ""
    
    primeiro = nomes[0].upper()
    prefixo_comum = ""
    
    for i, char in enumerate(primeiro):
        if all(len(nome) > i and nome.upper()[i] == char for nome in nomes):
            prefixo_comum += char
        else:
            break
    
    for pos in reversed(range(len(prefixo_comum))):
        if prefixo_comum[pos] in ['_', '-', ' ', '.']:
            return prefixo_comum[:pos+1].rstrip('_-. ')
    
    return prefixo_comum.rstrip('_-. ') if len(prefixo_comum) > 2 else ""


def _detectar_estruturas_dinamicas(nomes: List[str]) -> List[Dict]:
    """
    🔍 Detecta estruturas/templates comuns nos nomes
    """
    estruturas = Counter()
    
    for nome in nomes:
        template = nome
        template = re.sub(r'\b(19|20|21)\d{2}\b', 'YYYY', template)
        template = re.sub(r'\b(0[1-9]|1[0-2])\b', 'MM', template)
        template = re.sub(r'\b([0-2][0-9]|3[01])\b', 'DD', template)
        template = re.sub(r'\b\d+\b', 'NUM', template)
        template = re.sub(r'[_\-\s]+', '_', template)
        
        estruturas[template.upper()] += 1
    
    resultados = []
    for estrutura, freq in estruturas.most_common(3):
        if freq > 1:
            percentual = round((freq/len(nomes))*100, 1)
            exemplo = _encontrar_exemplo_estrutura_dinamica(nomes, estrutura)
            
            resultados.append({
                "template": estrutura,
                "frequencia": freq,
                "percentual": percentual,
                "exemplo": exemplo,
                "descricao": _descrever_template(estrutura)
            })
    
    return resultados


def _detectar_padroes_numericos(nomes: List[str]) -> Dict:
    """
    🔍 Detecta padrões numéricos dinamicamente (anos, sequências, etc.)
    """
    todos_numeros = []
    anos_detectados = []
    sequencias = []
    
    for nome in nomes:
        numeros = re.findall(r'\b\d+\b', nome)
        todos_numeros.extend([int(n) for n in numeros if n.isdigit()])
        
        anos = re.findall(r'\b(19\d{2}|20\d{2}|21\d{2})\b', nome)
        anos_detectados.extend(anos)
        
        sequencias_no_nome = re.findall(r'\b(0\d|[1-9]\d?)\b', nome)
        sequencias.extend([int(s) for s in sequencias_no_nome])
    
    resultado = {}
    
    if todos_numeros:
        resultado["numeros_encontrados"] = {
            "min": min(todos_numeros),
            "max": max(todos_numeros),
            "unicos": len(set(todos_numeros)),
            "total": len(todos_numeros)
        }
    
    if anos_detectados:
        anos_unicos = sorted(set(anos_detectados))
        resultado["anos"] = {
            "lista": anos_unicos,
            "range": f"{min(anos_unicos)}-{max(anos_unicos)}",
            "quantidade": len(anos_unicos)
        }
    
    if sequencias:
        seq_unicos = sorted(set(sequencias))
        if len(seq_unicos) > 2:
            resultado["sequencias"] = {
                "range": f"{min(seq_unicos):02d}-{max(seq_unicos):02d}",
                "quantidade": len(seq_unicos),
                "pode_ser_mes": max(seq_unicos) <= 12,
                "pode_ser_dia": max(seq_unicos) <= 31
            }
    
    return resultado


def _detectar_palavras_comuns(nomes: List[str]) -> List[Dict]:
    """
    🔍 Detecta palavras/tokens mais frequentes dinamicamente
    """
    todas_palavras = []
    
    for nome in nomes:
        nome_sem_ext = nome.split('.')[0] if '.' in nome else nome
        
        palavras = re.split(r'[_\-\s\.]+', nome_sem_ext.upper())
        
        palavras_validas = [
            p for p in palavras 
            if len(p) > 2 and not p.isdigit() and not re.match(r'^\d+$', p)
        ]
        
        todas_palavras.extend(palavras_validas)
    
    freq_palavras = Counter(todas_palavras)
    
    resultados = []
    for palavra, freq in freq_palavras.most_common(10):
        if freq > 1:  
            percentual = round((freq/len(nomes))*100, 1)
            exemplos = [nome for nome in nomes if palavra in nome.upper()][:2]
            
            resultados.append({
                "palavra": palavra,
                "frequencia": freq,
                "percentual": percentual,
                "exemplos": exemplos
            })
    
    return resultados


def _gerar_sugestoes_dinamicas(nomes: List[str], prefixos: List[Dict], padroes_num: Dict, palavras: List[Dict]) -> List[str]:
    """
    🔍 Gera sugestões completamente dinâmicas baseadas nos padrões detectados
    """
    sugestoes = []
    
    if prefixos:
        for prefixo_info in prefixos[:2]:  
            prefixo = prefixo_info["prefixo"]
            sugestoes.append(prefixo)
            
            if padroes_num.get("anos"):
                ano_recente = max(padroes_num["anos"]["lista"])
                sugestoes.append(f"{prefixo} {ano_recente}")
                
                if padroes_num.get("sequencias", {}).get("pode_ser_mes"):
                    sugestoes.extend([
                        f"{prefixo} {ano_recente} 01",
                        f"{prefixo} {ano_recente} 12"
                    ])
    
    if palavras:
        for palavra_info in palavras[:3]:  
            palavra = palavra_info["palavra"]
            if palavra not in ' '.join(sugestoes):  
                sugestoes.append(palavra)
                
                if padroes_num.get("anos"):
                    ano_recente = max(padroes_num["anos"]["lista"])
                    sugestoes.append(f"{palavra} {ano_recente}")
    
    if len(palavras) >= 2:
        palavra1 = palavras[0]["palavra"]
        palavra2 = palavras[1]["palavra"]
        sugestoes.append(f"{palavra1} {palavra2}")
    
    return list(dict.fromkeys(sugestoes))[:8]  


def _filtrar_prefixos_similares(prefixos: List[Dict]) -> List[Dict]:
    """Remove prefixos muito similares"""
    filtrados = []
    for prefixo in prefixos:
        if not any(
            prefixo["prefixo"] in p["prefixo"] or p["prefixo"] in prefixo["prefixo"] 
            for p in filtrados
        ):
            filtrados.append(prefixo)
    return filtrados[:3]  


def _encontrar_exemplo_estrutura_dinamica(nomes: List[str], template: str) -> str:
    """Encontra exemplo real para um template detectado"""
    for nome in nomes:
        nome_template = nome.upper()
        nome_template = re.sub(r'\b(19|20|21)\d{2}\b', 'YYYY', nome_template)
        nome_template = re.sub(r'\b(0[1-9]|1[0-2])\b', 'MM', nome_template)
        nome_template = re.sub(r'\b([0-2][0-9]|3[01])\b', 'DD', nome_template)
        nome_template = re.sub(r'\b\d+\b', 'NUM', nome_template)
        nome_template = re.sub(r'[_\-\s]+', '_', nome_template)
        
        if nome_template == template:
            return nome
    return ""


def _descrever_template(template: str) -> str:
    """Cria descrição legível do template"""
    descricao = template.replace('YYYY', 'ano').replace('MM', 'mês').replace('DD', 'dia').replace('NUM', 'número').replace('_', ' ')
    return f"Estrutura: {descricao}"


def _formatar_tamanho(size_bytes) -> str:
    """
    Converte tamanho em bytes para formato legível.
    """
    if not size_bytes:
        return "N/A"
    
    try:
        size_bytes = int(size_bytes)
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
    except (ValueError, TypeError):
        return str(size_bytes)