"""
Operações específicas para tarifas de concessionárias (MetrôRio, etc).
- leitura_tarifa: Consulta tarifas históricas com detecção automática de colunas
"""

import pandas as pd
from typing import Dict, Any, Optional


def _detectar_coluna_por_conteudo(
    df: pd.DataFrame,
    palavras_chave: list,
    usar_dados: bool = False
) -> Optional[int]:
    """
    Detecta coluna procurando por palavras-chave em nomes E dados.
    
    Args:
        df: DataFrame a analisar
        palavras_chave: Lista de palavras para procurar (ex: ["vigência", "vigeancia", "data"])
        usar_dados: Se True, procura também nos dados (primeiras 5 linhas)
    
    Returns:
        Índice da coluna encontrada ou None
    """
    # ============================================================
    # BUSCA 1: Nos nomes das colunas
    # ============================================================
    for idx, col_name in enumerate(df.columns):
        col_name_lower = str(col_name).lower()
        for palavra in palavras_chave:
            if palavra.lower() in col_name_lower:
                return idx
    
    # ============================================================
    # BUSCA 2: Nos dados (se habilitado)
    # ============================================================
    if usar_dados:
        # Procura nas primeiras 5 linhas
        for idx in range(min(5, len(df))):
            for col_idx, col_name in enumerate(df.columns):
                valor_str = str(df.iloc[idx, col_idx]).lower()
                for palavra in palavras_chave:
                    if palavra.lower() in valor_str and len(valor_str) > 3:
                        return col_idx
    
    return None


def _limpar_e_renomear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e renomeia colunas de forma inteligente.
    
    Faz:
    - Remove colunas totalmente vazias
    - Detecta cabeçalhos em múltiplas linhas
    - Renomeia "Unnamed: X" baseado em conteúdo
    - Unififica nomes
    
    Args:
        df: DataFrame com potenciais problemas estruturais
    
    Returns:
        DataFrame limpo e com colunas renomeadas
    """
    print(f"\n🔧 LIMPANDO E RENOMEANDO COLUNAS:")
    print(f"   Antes: {len(df.columns)} colunas")
    
    # ============================================================
    # PASSO 1: Remover colunas totalmente vazias
    # ============================================================
    df = df.dropna(axis=1, how='all')
    print(f"   ✅ Removidas colunas vazias: {len(df.columns)} restantes")
    
    # ============================================================
    # PASSO 2: Detectar se primeira linha é cabeçalho adicional
    # ============================================================
    primeira_linha = df.iloc[0] if len(df) > 0 else None
    
    # Se a primeira linha tem bastante texto (> 20 caracteres em média)
    # pode ser um cabeçalho adicional
    if primeira_linha is not None:
        media_tamanho = primeira_linha.astype(str).apply(len).mean()
        
        if media_tamanho > 20:
            print(f"   ⚠️ Primeira linha pode ser cabeçalho adicional (média: {media_tamanho:.0f} chars)")
            print(f"      Conteúdo: {primeira_linha.values[:3]}")
            
            # Usar primeira linha como novo cabeçalho
            novos_nomes = []
            for idx, val in enumerate(primeira_linha):
                val_str = str(val).strip()
                if val_str and val_str != 'nan':
                    novos_nomes.append(val_str)
                else:
                    novos_nomes.append(f"Col_{idx}")
            
            df.columns = novos_nomes
            df = df.iloc[1:].reset_index(drop=True)
            print(f"   ✅ Primeira linha usada como cabeçalho")
    
    # ============================================================
    # PASSO 3: Renomear colunas "Unnamed: X" por conteúdo
    # ============================================================
    novos_nomes = []
    
    for idx, col in enumerate(df.columns):
        col_str = str(col)
        
        # Se é "Unnamed", tenta deduzir nome do conteúdo
        if "unnamed" in col_str.lower():
            # Tira primeiros valores não-nulos desta coluna
            valores_amostra = df.iloc[:5, idx].dropna().unique()
            
            if len(valores_amostra) > 0:
                amostra_str = str(valores_amostra[0])[:30]
                novos_nomes.append(f"Col_{idx}_{amostra_str}")
            else:
                novos_nomes.append(f"Col_{idx}")
        else:
            novos_nomes.append(col_str)
    
    df.columns = novos_nomes
    print(f"   ✅ Colunas renomeadas:")
    for i, col in enumerate(df.columns):
        print(f"      [{i}] {col}")
    
    return df

def executar_leitura_tarifa(
    df: pd.DataFrame,
    consulta_tipo: str,
    ano: Optional[int] = None,
    arquivo_local: str = ""
) -> Dict[str, Any]:
    """
    Lê tarifas históricas de concessionárias (MetrôRio, CCR Barcas, SuperVia)
    com detecção automática de colunas.
    
    Tipos de consulta:
    1. 'atual' → Retorna TODAS as tarifas atuais (normal, social, etc)
    2. 'ano' → Retorna TODAS as tarifas vigentes em um ano específico
    3. 'ultima_mudanca' → Quando foi a última alteração
    4. 'historico' → Retorna histórico completo
    5. 'buscar_por_valor' → Busca tarifas abaixo de um valor
    
    Args:
        df: DataFrame com histórico de tarifas
        consulta_tipo: 'atual', 'ano', 'ultima_mudanca', 'historico', 'buscar_por_valor'
        ano: Ano a buscar (para 'ano') ou valor máximo (para 'buscar_por_valor')
        arquivo_local: Caminho do arquivo
    
    Returns:
        Dict com resultado formatado
    """
    print(f"\n💰 LEITURA_TARIFA:")

    print(f"   Tipo de consulta: {consulta_tipo}")
    print(f"   Shape original: {df.shape}")
    
    # ============================================================
    # PASSO 0: Limpar e renomear colunas
    # ============================================================
    df_original = df.copy()
    df = _limpar_e_renomear_colunas(df)
    
    # ============================================================
    # PASSO 1: Identificar colunas por conteúdo
    # ============================================================
    print(f"\n🔍 DETECTANDO COLUNAS:")
    
    # Coluna de TARIFA
    idx_tarifa = _detectar_coluna_por_conteudo(
        df,
        ["tarifa autorizada", "tarifa", "valor", "preço"],
        usar_dados=True
    )
    
    # Coluna de DATA
    idx_data = _detectar_coluna_por_conteudo(
        df,
        ["vigência", "vigeancia", "inicio", "data", "início"],
        usar_dados=True
    )
    
    # Coluna de DESCRIÇÃO
    idx_descricao = _detectar_coluna_por_conteudo(
        df,
        ["descrição", "descricao", "decreto", "deliberação", "deliberacao"],
        usar_dados=True
    )
    
    # ============================================================
    # VALIDAÇÃO: Colunas encontradas?
    # ============================================================
    if idx_tarifa is None:
        print(f"\n❌ ERRO: Coluna de TARIFA não encontrada")
        print(f"   Tentei procurar: ['tarifa autorizada', 'tarifa', 'valor', 'preço']")
        print(f"\n   Colunas disponíveis:")
        for i, col in enumerate(df.columns):
            print(f"      [{i}] {col}")
            print(f"          Amostra: {df.iloc[2:5, i].values}")
        return {
            "erro": "Coluna de tarifa não encontrada no arquivo",
            "colunas_detectadas": list(df.columns),
            "indices_testados": {
                "tarifa": idx_tarifa,
                "data": idx_data,
                "descricao": idx_descricao
            },
            "sucesso": False,
        }
    
    if idx_data is None:
        print(f"\n❌ ERRO: Coluna de DATA não encontrada")
        print(f"   Tentei procurar: ['vigência', 'vigeancia', 'inicio', 'data', 'início']")
        return {
            "erro": "Coluna de data de vigência não encontrada",
            "colunas_detectadas": list(df.columns),
            "sucesso": False,
        }
    
    # ============================================================
    # SUCESSO: Colunas identificadas
    # ============================================================
    coluna_tarifa = df.columns[idx_tarifa]
    coluna_data = df.columns[idx_data]
    coluna_descricao = df.columns[idx_descricao] if idx_descricao else None
    
    print(f"\n✅ COLUNAS IDENTIFICADAS:")
    print(f"   [{idx_tarifa}] TARIFA: {coluna_tarifa}")
    print(f"   [{idx_data}] DATA: {coluna_data}")
    print(f"   [{idx_descricao}] DESCRIÇÃO: {coluna_descricao}")
    
    # ============================================================
    # PASSO 2: Preparar dados
    # ============================================================
    df_copia = df.copy()
    
    # Converter data para datetime
    print(f"\n🔄 PREPARANDO DADOS:")
    df_copia[coluna_data] = pd.to_datetime(df_copia[coluna_data], errors='coerce', format="%d/%m/%Y")
    
    # Remover linhas com data inválida
    df_copia = df_copia.dropna(subset=[coluna_data])
    print(f"   ✅ Datas válidas: {len(df_copia)} linhas")
    
    # Converter tarifa para número
    df_copia[coluna_tarifa] = pd.to_numeric(df_copia[coluna_tarifa], errors='coerce')
    df_copia = df_copia.dropna(subset=[coluna_tarifa])
    print(f"   ✅ Tarifas válidas: {len(df_copia)} linhas")
    
    if df_copia.empty:
        print(f"❌ Nenhum dado válido encontrado")
        return {
            "erro": "Nenhum dado de tarifa válido encontrado",
            "sucesso": False,
        }
    
    # Extrair ano da data
    df_copia['_ano'] = df_copia[coluna_data].dt.year
    df_copia = df_copia.sort_values(by=coluna_data, ascending=False)
    
    print(f"   ✅ Dados preparados: {len(df_copia)} registros válidos")
    
    # ============================================================
    # CONSULTA: TARIFA ATUAL (TODAS as tarifas, diferenciadas por DESCRIÇÃO)
    # ============================================================
    if consulta_tipo == "atual":
        print(f"\n   📅 Buscando TODAS as tarifas atuais...")
        
        # Pega o primeiro registro (mais recente geral)
        registro_mais_recente = df_copia.iloc[0]
        data_mais_recente = pd.to_datetime(registro_mais_recente[coluna_data])
        
        # Filtra TODOS os registros com a mesma data mais recente
        registros_atuais = df_copia[df_copia[coluna_data] == data_mais_recente]
        
        print(f"   ✅ Encontrados {len(registros_atuais)} tipo(s) de tarifa na data mais recente")
        
        tarifas_atuais = []
        
        for idx, registro in registros_atuais.iterrows():
            tarifa_valor = float(registro[coluna_tarifa])
            descricao = str(registro[coluna_descricao]).strip() if coluna_descricao and coluna_descricao in registro.index else "Normal"
            
            # Classificar tipo de tarifa pela descrição
            tipo_tarifa = _classificar_tipo_tarifa(descricao)
            
            tarifas_atuais.append({
                "tipo": tipo_tarifa,
                "tarifa": round(tarifa_valor, 2),
                "descricao": descricao,
                "data_vigencia": data_mais_recente.strftime('%d/%m/%Y'),
                "data_vigencia_iso": data_mais_recente.strftime('%Y-%m-%d'),
            })
            
            print(f"      • {tipo_tarifa}: R$ {tarifa_valor:.2f} ({descricao})")
        
        # Ordenar: Normal primeiro, depois Social, depois outros
        ordem_tipos = {"Normal": 0, "Social": 1, "Outros": 2}
        tarifas_atuais.sort(key=lambda x: ordem_tipos.get(x["tipo"], 3))
        
        return {
            "consulta_tipo": "atual",
            "tarifas": tarifas_atuais,
            "data_vigencia": data_mais_recente.strftime('%d/%m/%Y'),
            "arquivo_local": arquivo_local,
            "sucesso": True,
        }
    
    # ============================================================
    # CONSULTA: TARIFA EM UM ANO ESPECÍFICO (TODAS as tarifas)
    # ============================================================
    elif consulta_tipo == "ano":
        if not ano:
            print(f"❌ Parâmetro 'ano' obrigatório para consulta_tipo='ano'")
            return {
                "erro": "Parâmetro 'ano' é obrigatório",
                "sucesso": False,
            }
        
        print(f"\n   📅 Buscando TODAS as tarifas para o ano {int(ano)}...")
        
        # Filtrar registros do ano
        registros_ano = df_copia[df_copia['_ano'] == int(ano)]
        
        if registros_ano.empty:
            print(f"❌ Nenhuma tarifa encontrada para {int(ano)}")
            anos_disponiveis = sorted(df_copia['_ano'].unique())
            return {
                "erro": f"Nenhuma tarifa encontrada para {int(ano)}",
                "anos_disponiveis": [int(a) for a in anos_disponiveis],
                "sucesso": False,
            }
        
        # Pega a data mais recente daquele ano
        data_mais_recente_ano = registros_ano[coluna_data].max()
        registros_vigentes = registros_ano[registros_ano[coluna_data] == data_mais_recente_ano]
        
        print(f"   ✅ Encontrados {len(registros_vigentes)} tipo(s) de tarifa vigente em {int(ano)}")
        
        tarifas_ano = []
        
        for idx, registro in registros_vigentes.iterrows():
            tarifa_valor = float(registro[coluna_tarifa])
            descricao = str(registro[coluna_descricao]).strip() if coluna_descricao and coluna_descricao in registro.index else "Normal"
            tipo_tarifa = _classificar_tipo_tarifa(descricao)
            
            tarifas_ano.append({
                "tipo": tipo_tarifa,
                "tarifa": round(tarifa_valor, 2),
                "descricao": descricao,
                "data_vigencia": data_mais_recente_ano.strftime('%d/%m/%Y'),
                "data_vigencia_iso": data_mais_recente_ano.strftime('%Y-%m-%d'),
            })
            
            print(f"      • {tipo_tarifa}: R$ {tarifa_valor:.2f} ({descricao})")
        
        # Ordenar: Normal primeiro, depois Social, depois outros
        ordem_tipos = {"Normal": 0, "Social": 1, "Outros": 2}
        tarifas_ano.sort(key=lambda x: ordem_tipos.get(x["tipo"], 3))
        
        return {
            "consulta_tipo": "ano",
            "ano": int(ano),
            "tarifas": tarifas_ano,
            "data_vigencia": data_mais_recente_ano.strftime('%d/%m/%Y'),
            "arquivo_local": arquivo_local,
            "sucesso": True,
        }
    
    # ============================================================
    # CONSULTA: ÚLTIMA MUDANÇA
    # ============================================================
    elif consulta_tipo == "ultima_mudanca":
        print(f"\n   📅 Buscando última mudança de tarifa...")
        
        # Pega o primeiro registro (mais recente)
        registro = df_copia.iloc[0]
        
        tarifa_valor = float(registro[coluna_tarifa])
        data_vigencia = pd.to_datetime(registro[coluna_data])
        descricao = str(registro[coluna_descricao]).strip() if coluna_descricao and coluna_descricao in registro.index else "N/A"
        tipo_tarifa = _classificar_tipo_tarifa(descricao)
        
        # Calcular dias desde mudança
        hoje = pd.Timestamp.now()
        dias_desde = (hoje - data_vigencia).days
        
        print(f"   ✅ Encontrado!")
        print(f"      Tipo: {tipo_tarifa}")
        print(f"      Data: {data_vigencia.strftime('%d/%m/%Y')}")
        print(f"      Há {dias_desde} dias")
        print(f"      Tarifa: R$ {tarifa_valor:.2f}")
        print(f"      Descrição: {descricao}")
        
        return {
            "consulta_tipo": "ultima_mudanca",
            "tipo": tipo_tarifa,
            "tarifa": round(tarifa_valor, 2),
            "data_mudanca": data_vigencia.strftime('%d/%m/%Y'),
            "data_mudanca_iso": data_vigencia.strftime('%Y-%m-%d'),
            "dias_desde_mudanca": int(dias_desde),
            "descricao": descricao,
            "arquivo_local": arquivo_local,
            "sucesso": True,
        }
    
    # ============================================================
    # CONSULTA: HISTÓRICO (últimas 20 linhas)
    # ============================================================

    elif consulta_tipo == "historico":
        print(f"\n   📚 Buscando histórico COMPLETO de tarifas...")
        
        registros = df_copia  
        
        historico = []
        for idx, registro in registros.iterrows():
            tarifa_valor = float(registro[coluna_tarifa])
            data_vigencia = pd.to_datetime(registro[coluna_data])
            descricao = str(registro[coluna_descricao]).strip() if coluna_descricao and coluna_descricao in registro.index else "N/A"
            tipo_tarifa = _classificar_tipo_tarifa(descricao)
            
            historico.append({
                "tipo": tipo_tarifa,
                "tarifa": round(tarifa_valor, 2),
                "data_vigencia": data_vigencia.strftime('%d/%m/%Y'),
                "data_vigencia_iso": data_vigencia.strftime('%Y-%m-%d'),
                "ano": int(data_vigencia.year),
                "descricao": descricao
            })
        
        tarifas_valores = [h["tarifa"] for h in historico]
        
        print(f"   ✅ Encontrados {len(historico)} registros")
        print(f"   📊 Menor: R$ {min(tarifas_valores):.2f} | Maior: R$ {max(tarifas_valores):.2f}")
        for i, h in enumerate(historico[:3], 1):
            print(f"      {i}. {h['tipo']}: R$ {h['tarifa']:.2f} - {h['data_vigencia']}")
        
        return {
            "consulta_tipo": "historico",
            "total_registros": len(historico),
            "historico": historico,
            "menor_tarifa": min(tarifas_valores),
            "maior_tarifa": max(tarifas_valores),
            "arquivo_local": arquivo_local,
            "sucesso": True,
        }

    elif consulta_tipo == "buscar_por_valor":
        valor_max = ano  # Reutiliza parâmetro 'ano' como valor máximo
        
        if valor_max is None:
            return {
                "erro": "Parâmetro 'ano' é usado como valor_max para buscar_por_valor",
                "sucesso": False,
            }
        
        valor_max = float(valor_max)
        print(f"\n   🔍 Buscando tarifas <= R$ {valor_max:.2f}...")
        
        resultados = df_copia[df_copia[coluna_tarifa] <= valor_max].copy()
        resultados = resultados.sort_values(by=coluna_data, ascending=False)
        
        if resultados.empty:
            return {
                "consulta_tipo": "buscar_por_valor",
                "valor_max": valor_max,
                "mensagem": f"Nenhuma tarifa encontrada abaixo de R$ {valor_max:.2f}",
                "menor_tarifa_historica": round(float(df_copia[coluna_tarifa].min()), 2),
                "sucesso": True,
            }
        
        encontrados = []
        for idx, registro in resultados.iterrows():
            tarifa_valor = float(registro[coluna_tarifa])
            data_vigencia = pd.to_datetime(registro[coluna_data])
            descricao = str(registro[coluna_descricao]).strip() if coluna_descricao and coluna_descricao in registro.index else "N/A"
            tipo_tarifa = _classificar_tipo_tarifa(descricao)
            
            encontrados.append({
                "tipo": tipo_tarifa,
                "tarifa": round(tarifa_valor, 2),
                "data_vigencia": data_vigencia.strftime('%d/%m/%Y'),
                "data_vigencia_iso": data_vigencia.strftime('%Y-%m-%d'),
                "ano": int(data_vigencia.year),
                "descricao": descricao
            })
        
        print(f"   ✅ Encontrados {len(encontrados)} registros <= R$ {valor_max:.2f}")
        
        return {
            "consulta_tipo": "buscar_por_valor",
            "valor_max": valor_max,
            "total_encontrados": len(encontrados),
            "resultados": encontrados,
            "arquivo_local": arquivo_local,
            "sucesso": True,
        }

    else:
        print(f"❌ Tipo de consulta desconhecido: {consulta_tipo}")
        return {
            "erro": f"Tipo de consulta desconhecido: {consulta_tipo}",
            "tipos_disponiveis": ["atual", "ano", "ultima_mudanca", "historico"],
            "sucesso": False,
        }
    

def _classificar_tipo_tarifa(descricao: str) -> str:
    """
    Classifica o tipo de tarifa baseado na descrição.
    
    Args:
        descricao: Descrição da tarifa
    
    Returns:
        "Normal", "Social", ou "Outros"
    """
    desc_lower = str(descricao).lower()
    
    if "social" in desc_lower:
        return "Social"
    elif "inteira" in desc_lower or "normal" in desc_lower or "autorizada" in desc_lower:
        return "Normal"
    else:
        return "Outros"