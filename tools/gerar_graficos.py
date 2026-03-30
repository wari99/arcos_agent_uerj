import os
import traceback
from typing import Any, Dict, List, Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from langchain.tools import tool

matplotlib.use('Agg')

from tools.baixar_arquivo_dados import (
    obter_cache_arquivos,
    obter_pasta_temporaria,
)

plt.style.use('seaborn-v0_8-darkgrid')
CORES_PADRAO = ['#ace7ff', '#ffb5e8', '#bffcc6', '#a79aff', '#f48a94', '#8c564b', '#fff7d2', '#7f7f7f']

@tool("gerar_graficos")
def gerar_graficos(params: dict) -> Any:
    """
    Gera visualizações gráficas (barras, linhas, pizza ou comparacao) de dados já baixados.
    
    USE ESTA TOOL APENAS quando usuário EXPLICITAMENTE pedir:
    - "me mostra um gráfico"
    - "pode gerar uma visualização"
    - "quero ver em forma de gráfico"
    - "faz um gráfico de..."
    
    Para análises textuais/numéricas, use analisar_dados_arquivo.
    
    Parâmetros obrigatórios:
      - tipo_grafico: 'barras', 'linhas', 'pizza' ou 'comparacao'
      - arquivos: lista de file_filters ou nomes de arquivos (ex: ["2025_12_01", "2025_12_02"])
      
    Parâmetros para agregação (quando há categorias repetidas):
      - coluna_categoria: coluna para agrupar/categorizar (ex: "TIPO_GRATUIDADE", "MODAL")
      - coluna_valor: coluna numérica para somar/calcular (ex: "QUANTIDADE_TRANSACAO")
      - operacao: 'soma' (padrão), 'media' ou 'contagem'
      
    Outros:
      - titulo: título do gráfico (opcional)
      - top_n: limitar a N categorias (padrão: 15 para barras/pizza)
    
    Lógica de agregação:
    - Se houver múltiplas linhas com mesmo valor em coluna_categoria (ex: 3 linhas "Idoso"),
      a tool SOMA automaticamente os valores de coluna_valor para cada categoria única.
    - Exemplo: 3 linhas "Idoso" com valores [5000, 5000, 5000] → Total Idoso = 15.000
    
    Exemplos de uso:
    
    1) Comparar total de transações por tipo de gratuidade (COM AGREGAÇÃO):
       {
         "tipo_grafico": "barras",
         "arquivos": ["2025_12_01"],
         "coluna_categoria": "TIPO_GRATUIDADE",
         "coluna_valor": "QUANTIDADE_TRANSACAO",
         "operacao": "soma"
       }
    
    2) Comparar totais entre múltiplos arquivos:
       {
         "tipo_grafico": "comparacao",
         "arquivos": ["2025_12_01", "2025_12_02"],
         "coluna_valor": "QUANTIDADE_TRANSACAO",
         "operacao": "soma"
       }
    
    3) Evolução temporal:
       {
         "tipo_grafico": "linhas",
         "arquivos": ["2025_12_01", "2025_12_02", "2025_12_03"],
         "coluna_valor": "QUANTIDADE_TRANSACAO",
         "operacao": "soma"
       }
    
    4) Distribuição percentual:
       {
         "tipo_grafico": "pizza",
         "arquivos": ["2025_12_01"],
         "coluna_categoria": "TIPO_GRATUIDADE",
         "coluna_valor": "QUANTIDADE_TRANSACAO",
         "operacao": "soma"
       }
    """
    
    try:
        tipo_grafico = params.get("tipo_grafico", "barras")
        arquivos_solicitados = params.get("arquivos", [])
        coluna_categoria = params.get("coluna_categoria") 
        coluna_valor = params.get("coluna_valor")  
        titulo = params.get("titulo", "")
        operacao = params.get("operacao", "soma")
        top_n = params.get("top_n", 15)
        
        print("🎨 DEBUG - Parâmetros recebidos para gerar_graficos:")
        print(f"   tipo_grafico: {tipo_grafico}")
        print(f"   arquivos: {arquivos_solicitados}")
        print(f"   coluna_categoria: {coluna_categoria}")
        print(f"   coluna_valor: {coluna_valor}")
        print(f"   operacao: {operacao}")
        
        if tipo_grafico not in ["barras", "linhas", "pizza", "comparacao"]:
            return {
                "erro": f"Tipo de gráfico '{tipo_grafico}' não suportado",
                "tipos_validos": ["barras", "linhas", "pizza", "comparacao"],
                "sucesso": False
            }
        
        if not arquivos_solicitados:
            return {
                "erro": "Parâmetro 'arquivos' é obrigatório (lista de file_filters)",
                "exemplo": '["2025_12_01", "2025_12_02"]',
                "sucesso": False
            }
        
        try:
            cache_arquivos = obter_cache_arquivos()
            pasta_temp = obter_pasta_temporaria()
            print(f"📂 DEBUG - Cache tem {len(cache_arquivos)} arquivos")
        except Exception as e:
            return {
                "erro": f"Erro ao acessar cache: {str(e)}",
                "sucesso": False
            }
        
        if not cache_arquivos:
            return {
                "erro": "Nenhum arquivo disponível no cache. Baixe arquivos primeiro usando baixar_arquivo_dados.",
                "sucesso": False
            }
        
        dataframes_selecionados: List[Dict] = []
        
        for arquivo_filtro in arquivos_solicitados:
            encontrado = False
            for chave, info_cache in cache_arquivos.items():
                nome_arquivo = info_cache.get("nome", "")
                if arquivo_filtro.lower() in nome_arquivo.lower():
                    if os.path.exists(info_cache["arquivo_local"]):
                        dataframes_selecionados.append({
                            "nome": nome_arquivo,
                            "df": info_cache["dataframe"],
                            "filtro": arquivo_filtro
                        })
                        print(f"✅ Arquivo encontrado: {nome_arquivo}")
                        encontrado = True
                        break
            
            if not encontrado:
                print(f"⚠️ Arquivo não encontrado no cache: {arquivo_filtro}")
        
        if not dataframes_selecionados:
            return {
                "erro": f"Nenhum dos arquivos solicitados está no cache",
                "arquivos_solicitados": arquivos_solicitados,
                "arquivos_disponiveis": [info["nome"] for info in cache_arquivos.values()],
                "sucesso": False
            }
        
        print(f"📊 Gerando gráfico... :'{tipo_grafico}' com {len(dataframes_selecionados)} arquivo(s)")
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        if tipo_grafico == "barras":
            resultado = _gerar_grafico_barras(
                ax, dataframes_selecionados, coluna_categoria, coluna_valor, 
                operacao, titulo, top_n
            )
            
        elif tipo_grafico == "comparacao":
            resultado = _gerar_grafico_comparacao(
                ax, dataframes_selecionados, coluna_valor, operacao, titulo
            )
            
        elif tipo_grafico == "linhas":
            resultado = _gerar_grafico_linhas(
                ax, dataframes_selecionados, coluna_valor, operacao, titulo
            )
            
        elif tipo_grafico == "pizza":
            resultado = _gerar_grafico_pizza(
                ax, dataframes_selecionados, coluna_categoria, coluna_valor,
                operacao, titulo, top_n
            )
        
        if not resultado.get("sucesso"):
            plt.close(fig)
            return resultado
        
        try:
            nome_arquivo_grafico = f"grafico_{tipo_grafico}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
            caminho_grafico = os.path.join(pasta_temp, nome_arquivo_grafico)
            
            plt.tight_layout()
            plt.savefig(caminho_grafico, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            print(f"✅ Gráfico salvo: {caminho_grafico}")
            
            return {
                "sucesso": True,
                "caminho_grafico": caminho_grafico,
                "nome_arquivo": nome_arquivo_grafico,
                "tipo_grafico": tipo_grafico,
                "arquivos_usados": [df["nome"] for df in dataframes_selecionados],
                "mensagem": f"Gráfico de {tipo_grafico} gerado com sucesso!",
                "insights": resultado.get("insights", "")
            }
            
        except Exception as e:
            plt.close(fig)
            return {
                "erro": f"Erro ao salvar gráfico: {str(e)}",
                "sucesso": False,
                "traceback": traceback.format_exc()
            }
        
    except Exception as e:
        error_msg = f"Erro geral: {str(e)}"
        print(f"❌ DEBUG - {error_msg}")
        print(f"❌ DEBUG - Traceback: {traceback.format_exc()}")
        return {
            "erro": error_msg,
            "sucesso": False,
            "traceback": traceback.format_exc()
        }

def _gerar_grafico_barras(ax, dataframes: List[Dict], coluna_categoria: Optional[str],
                          coluna_valor: Optional[str], operacao: str, titulo: str, 
                          top_n: int) -> Dict:
    """
    Gera gráfico de barras com AGREGAÇÃO automática.
    
    Se tiver múltiplas linhas com mesmo valor em coluna_categoria (ex: "Idoso", "Idoso", "Idoso"),
    SOMA automaticamente os valores de coluna_valor para cada categoria única.
    """
    try:
        if len(dataframes) != 1:
            return {
                "erro": "Gráfico de barras com categorias requer exatamente 1 arquivo. Use tipo='comparacao' para múltiplos arquivos.",
                "sucesso": False
            }
        
        df = dataframes[0]["df"]
        
        if not coluna_categoria:
            return {
                "erro": "Para gráfico de barras, 'coluna_categoria' é obrigatória",
                "exemplo": "coluna_categoria='TIPO_GRATUIDADE'",
                "sucesso": False
            }
        
        if coluna_categoria not in df.columns:
            return {
                "erro": f"Coluna '{coluna_categoria}' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False
            }
        
        if coluna_valor and coluna_valor in df.columns:
            print(f"🔢 Agregando: groupby('{coluna_categoria}')['{coluna_valor}'].{operacao}()")
            
            if operacao == "soma":
                dados = df.groupby(coluna_categoria)[coluna_valor].sum().sort_values(ascending=False)
            elif operacao == "media":
                dados = df.groupby(coluna_categoria)[coluna_valor].mean().sort_values(ascending=False)
            else:  
                dados = df.groupby(coluna_categoria)[coluna_valor].count().sort_values(ascending=False)
            
            ylabel = f'{operacao.capitalize()} de {coluna_valor}'
        else:
            dados = df[coluna_categoria].value_counts()
            ylabel = 'Frequência'
        
        dados = dados.head(top_n)
        
        print(f"📊 Dados agregados: {dados.to_dict()}")
        
        bars = ax.bar(range(len(dados)), dados.values, color=CORES_PADRAO[:len(dados)])
        ax.set_xticks(range(len(dados)))
        ax.set_xticklabels(dados.index, rotation=45, ha='right')
        ax.set_xlabel(coluna_categoria, fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(titulo or f'{ylabel} por {coluna_categoria}', fontsize=14, fontweight='bold')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=9)
        
        ax.grid(axis='y', alpha=0.3)
        
        insights = f"Top {len(dados)} categorias: {', '.join([f'{k} ({v:,.0f})' for k, v in dados.head(3).items()])}"
        
        return {"sucesso": True, "insights": insights}
        
    except Exception as e:
        return {
            "erro": f"Erro ao gerar gráfico de barras: {str(e)}",
            "traceback": traceback.format_exc(),
            "sucesso": False
        }


def _gerar_grafico_comparacao(ax, dataframes: List[Dict], coluna_valor: Optional[str],
                               operacao: str, titulo: str) -> Dict:
    """
    Gera gráfico de barras comparando TOTAIS entre múltiplos arquivos.
    Cada barra = 1 arquivo (ex: dia 1 vs dia 2).
    """
    try:
        if len(dataframes) < 2:
            return {
                "erro": "Gráfico de comparação requer pelo menos 2 arquivos",
                "sucesso": False
            }
        
        labels = []
        valores = []
        
        for df_info in dataframes:
            df = df_info["df"]
            filtro = df_info["filtro"]
            
            if coluna_valor and coluna_valor in df.columns:
                if operacao == "soma":
                    valor = df[coluna_valor].sum()
                elif operacao == "media":
                    valor = df[coluna_valor].mean()
                else:
                    valor = df[coluna_valor].count()
            else:
                valor = len(df)
            
            labels.append(filtro)
            valores.append(valor)
            print(f"📊 {filtro}: {valor:,.0f}")
        
        bars = ax.bar(labels, valores, color=CORES_PADRAO[:len(labels)])
        ax.set_xlabel('Período', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{operacao.capitalize()} de {coluna_valor or "registros"}', 
                     fontsize=12, fontweight='bold')
        ax.set_title(titulo or f'Comparação entre Arquivos', fontsize=14, fontweight='bold')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=10)
        
        plt.xticks(rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)
        
        if len(valores) >= 2:
            variacao = ((valores[-1] - valores[0]) / valores[0]) * 100
            insights = f"Variação de {variacao:+.1f}% entre primeiro e último período"
        else:
            insights = ""
        
        return {"sucesso": True, "insights": insights}
        
    except Exception as e:
        return {
            "erro": f"Erro ao gerar gráfico de comparação: {str(e)}",
            "traceback": traceback.format_exc(),
            "sucesso": False
        }


def _gerar_grafico_linhas(ax, dataframes: List[Dict], coluna_valor: Optional[str],
                          operacao: str, titulo: str) -> Dict:
    """
    Gera gráfico de linhas (evolução temporal entre múltiplos arquivos).
    """
    try:
        if len(dataframes) < 2:
            return {
                "erro": "Gráfico de linhas requer pelo menos 2 arquivos para mostrar evolução",
                "sucesso": False
            }
        
        labels = []
        valores = []
        
        for df_info in dataframes:
            df = df_info["df"]
            filtro = df_info["filtro"]
            
            if coluna_valor and coluna_valor in df.columns:
                if operacao == "soma":
                    valor = df[coluna_valor].sum()
                elif operacao == "media":
                    valor = df[coluna_valor].mean()
                else:
                    valor = df[coluna_valor].count()
            else:
                valor = len(df)
            
            labels.append(filtro)
            valores.append(valor)
        
        ax.plot(labels, valores, marker='o', linewidth=2, markersize=8, color=CORES_PADRAO[0])
        ax.set_xlabel('Período', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{operacao.capitalize()} de {coluna_valor or "registros"}', 
                     fontsize=12, fontweight='bold')
        ax.set_title(titulo or 'Evolução Temporal', fontsize=14, fontweight='bold')
        
        for i, (label, valor) in enumerate(zip(labels, valores)):
            ax.text(i, valor, f'{valor:,.0f}', ha='center', va='bottom', fontsize=9)
        
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, alpha=0.3)
        
        if len(valores) >= 2:
            variacao = ((valores[-1] - valores[0]) / valores[0]) * 100
            insights = f"Tendência: {variacao:+.1f}% do início ao fim"
        else:
            insights = ""
        
        return {"sucesso": True, "insights": insights}
        
    except Exception as e:
        return {
            "erro": f"Erro ao gerar gráfico de linhas: {str(e)}",
            "traceback": traceback.format_exc(),
            "sucesso": False
        }


def _gerar_grafico_pizza(ax, dataframes: List[Dict], coluna_categoria: Optional[str],
                        coluna_valor: Optional[str], operacao: str, titulo: str,
                        top_n: int) -> Dict:
    """
    Gera gráfico de pizza (distribuição percentual) com AGREGAÇÃO automática.
    """
    try:
        if len(dataframes) > 1:
            return {
                "erro": "Gráfico de pizza suporta apenas 1 arquivo",
                "sucesso": False
            }
        
        df = dataframes[0]["df"]
        
        if not coluna_categoria:
            return {
                "erro": "Para gráfico de pizza, 'coluna_categoria' é obrigatória",
                "sucesso": False
            }
        
        if coluna_categoria not in df.columns:
            return {
                "erro": f"Coluna '{coluna_categoria}' não encontrada",
                "colunas_disponiveis": list(df.columns),
                "sucesso": False
            }
        
        if coluna_valor and coluna_valor in df.columns:
            if operacao == "soma":
                dados = df.groupby(coluna_categoria)[coluna_valor].sum().sort_values(ascending=False)
            elif operacao == "media":
                dados = df.groupby(coluna_categoria)[coluna_valor].mean().sort_values(ascending=False)
            else:
                dados = df.groupby(coluna_categoria)[coluna_valor].count().sort_values(ascending=False)
        else:
            dados = df[coluna_categoria].value_counts()
        
        dados = dados.head(top_n)
        
        wedges, texts, autotexts = ax.pie(
            dados.values,
            labels=dados.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=CORES_PADRAO[:len(dados)],
            textprops={'fontsize': 10}
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title(titulo or f'Distribuição de {coluna_categoria}', fontsize=14, fontweight='bold')
        
        insights = f"Maior categoria: {dados.index[0]} ({dados.iloc[0]/dados.sum()*100:.1f}%)"
        
        return {"sucesso": True, "insights": insights}
        
    except Exception as e:
        return {
            "erro": f"Erro ao gerar gráfico de pizza: {str(e)}",
            "traceback": traceback.format_exc(),
            "sucesso": False
        }