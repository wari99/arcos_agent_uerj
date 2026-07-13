import os
import traceback
from typing import Any, Dict
import pandas as pd
from langchain.tools import tool

from tools.commons.settings import FAIXAS_HORARIAS
from tools.gerenciar_cache_sessao import obter_arquivos_para_analise

from tools.commons.utils import (
    obter_pasta_temporaria,
)

from .commons._operacoes_basicas import (
    executar_contar_linhas,
    executar_mostrar_colunas,
    executar_preview,
    executar_estatistica,
)

from .commons._operacoes_turnos import (
    _determinar_faixa_horaria,
    executar_filtrar_por_turno,
)

from .commons._operacoes_filtros import (
    executar_contar_por_valor,
    executar_agrupar_e_somar,
)
 
from .commons._operacoes_concessionarias import (
    executar_leitura_tarifa, 
)
@tool("analisar_dados_arquivo")
def analisar_dados_arquivo(params: dict) -> Any:
    """
    Executa operações de análise em arquivos já baixados/processados.

    params:
      - package_id: id da base (ex: 'setram_sgr')
      - file_filter: filtro do nome do arquivo (ex: '2025_12_20' ou nome completo)
      - operation: tipo de operação:
          - 'contar_linhas': conta total de linhas
          - 'mostrar_colunas': lista colunas disponíveis
          - 'preview': mostra primeiras 5 linhas
          - 'contar_por_valor': conta quantas LINHAS têm determinado valor
          - 'agrupar_e_somar': FILTRA por valor E SOMA outra coluna (para totais)
          - 'media', 'soma', 'max', 'min': estatísticas gerais
          - 'filtrar_por_turno': filtra por faixa horária E tipo de gratuidade/modal
          - 'contar_por_turno': conta qual turno teve mais uso
      
      Para 'contar_por_valor':
      - column: coluna para filtrar (ex: "TIPO_GRATUIDADE")
      - value: valor a buscar (ex: "Idoso")
      
      Para 'agrupar_e_somar':
      - filter_column: coluna para filtrar (ex: "TIPO_GRATUIDADE")
      - filter_value: valor a filtrar (ex: "Idoso")
      - sum_column: coluna numérica para somar (ex: "QUANTIDADE_TRANSACAO")
      
      Para 'filtrar_por_turno':
      - turno: número da faixa (0=manhã, 1=tarde, 2=noite, 3=madrugada) ou "todos"
      - filter_column: coluna para filtrar ADICIONAL (ex: "Descricao da Aplicação")
      - filter_value: valor a buscar ADICIONAL (ex: "Idoso")
      - data_coluna: nome da coluna com datetime (padrão: "Data da Transação")
      
      Para 'contar_por_turno':
      - filter_column: coluna para filtrar (ex: "Descricao da Aplicação")
      - filter_value: valor a buscar (ex: "Idoso")
      - data_coluna: nome da coluna com datetime (padrão: "Data da Transação")
    """

    try:
        package_id = params.get("package_id")
        file_filter = params.get("file_filter", "")
        operation = params.get("operation", "contar_linhas")

        print("\n" + "="*80)
        print("📋 DEBUG - ANALISAR_DADOS_ARQUIVO - INÍCIO")
        print("="*80)
        print(f"   package_id: {package_id}")
        print(f"   file_filter: {file_filter}")
        print(f"   operation: {operation}")
        print("="*80)

        if not package_id:
            return {
                "erro": "Parâmetro 'package_id' é obrigatório.",
                "sucesso": False,
            }
        print(f"\n🔍 Obtendo arquivos para análise...")  
        resultado_obtencao = obter_arquivos_para_analise(
            package_id=package_id,
            file_filter=file_filter,
            força_download=False
        )
        
        if not resultado_obtencao.get("sucesso"):
            erro = resultado_obtencao.get("erro", "Erro desconhecido")
            print(f"❌ Erro ao obter arquivos: {erro}")
            return {
                "erro": erro,
                "sucesso": False
            }
        
        arquivos_para_analisar = resultado_obtencao.get("arquivos", [])
        print(f"✅ {len(arquivos_para_analisar)} arquivo(s) obtido(s)")       
        print(f"\n{'='*80}")
        print(f"📊 PROCESSANDO {len(arquivos_para_analisar)} ARQUIVO(S)")
        print(f"{'='*80}")

        resultados: Dict[str, Any] = {}
        arquivos_analisados = 0


        for arquivo_info in arquivos_para_analisar:
            try:
                df: pd.DataFrame = arquivo_info["df"]
                nome = arquivo_info["nome"]

                print(f"\n{'='*80}")
                print(f"📊 ANALISANDO: {nome}")
                print(f"{'='*80}")
                print(f"   Shape: {df.shape} (linhas x colunas)")
                print(f"   Colunas: {list(df.columns)}")

                if operation == "contar_linhas":
                    resultados[nome] = executar_contar_linhas(df, arquivo_info["arquivo_local"])

                elif operation == "mostrar_colunas":
                    resultados[nome] = executar_mostrar_colunas(df, arquivo_info["arquivo_local"])

                elif operation == "preview":
                    resultados[nome] = executar_preview(df, arquivo_info["arquivo_local"])

                elif operation == "contar_por_valor":
                    resultados[nome] = executar_contar_por_valor(
                        df=df,
                        coluna=params.get("column"),
                        valor=params.get("value"),
                        arquivo_local=arquivo_info["arquivo_local"]
                    )

                elif operation == "agrupar_e_somar":
                    resultados[nome] = executar_agrupar_e_somar(
                        df=df,
                        filter_column=params.get("filter_column"),
                        filter_value=params.get("filter_value"),
                        sum_column=params.get("sum_column"),
                        arquivo_local=arquivo_info["arquivo_local"]
                    )

                elif operation == "filtrar_por_turno":
                    turno = params.get("turno", "todos")
                    filter_column = params.get("filter_column")
                    filter_value = params.get("filter_value")
                    data_coluna = params.get("data_coluna", "Data da Transação")

                    resultados[nome] = executar_filtrar_por_turno(
                        df=df,
                        turno=turno,
                        data_coluna=data_coluna,
                        arquivo_local=arquivo_info["arquivo_local"],
                        filter_column=filter_column,
                        filter_value=filter_value,
                    )

                elif operation == "comparar_por_turno":
                    """
                    Agregação por turno para gráficos e comparações.
                    Retorna contagem de transações por turno.
                    
                    Exemplo de resposta:
                    {
                        "dados_turno": [
                            {"Turno": "Manhã", "Quantidade": 64560, "Intervalo": "06:01 até 12:00"},
                            {"Turno": "Tarde", "Quantidade": 29223, "Intervalo": "12:01 até 18:00"},
                            ...
                        ],
                        "sucesso": True
                    }
                    """
                    filter_column = params.get("filter_column")
                    filter_value = params.get("filter_value")
                    data_coluna = params.get("data_coluna", "Data da Transação")
                    
                    print(f"\n📊 COMPARAR_POR_TURNO:")
                    print(f"   Filtro: {filter_column}='{filter_value}' (opcional)")
                    
                    try:
                        if data_coluna not in df.columns:
                            resultados[nome] = {
                                "erro": f"Coluna de data '{data_coluna}' não encontrada",
                                "colunas_disponiveis": list(df.columns),
                                "sucesso": False,
                            }
                            print(f"❌ Coluna '{data_coluna}' não existe")
                            continue
                        
                        df[data_coluna] = pd.to_datetime(df[data_coluna], errors='coerce')
                        
                        df['_hora'] = df[data_coluna].dt.hour
                        df['_minuto'] = df[data_coluna].dt.minute
                        df['_turno'] = df.apply(
                            lambda row: _determinar_faixa_horaria(row['_hora'], row['_minuto']),
                            axis=1
                        )
                        
                        print(f"✅ Datas e turnos processados")
                        df_filtrado = df.copy()                  
                        if filter_column and filter_value:
                            if filter_column not in df_filtrado.columns:
                                resultados[nome] = {
                                    "erro": f"Coluna de filtro '{filter_column}' não encontrada",
                                    "colunas_disponiveis": list(df.columns),
                                    "sucesso": False,
                                }
                                print(f"❌ Coluna '{filter_column}' não existe")
                                continue
                            
                            df_filtrado = df_filtrado[
                                df_filtrado[filter_column].astype(str).str.contains(str(filter_value), case=False, na=False)
                            ]
                            total_com_filtro = len(df_filtrado)
                            print(f"✅ Filtrado: {total_com_filtro} linhas com '{filter_value}'")
                            
                            if total_com_filtro == 0:
                                resultados[nome] = {
                                    "erro": f"Nenhuma transação encontrada para filtro {filter_column}='{filter_value}'",
                                    "sucesso": False,
                                }
                                print(f"❌ Nenhuma linha encontrada para filtro")
                                continue

                        dados_turno = []
                        for t in range(4):
                            count = len(df_filtrado[df_filtrado['_turno'] == t])
                            
                            if count > 0:
                                info_turno = FAIXAS_HORARIAS[t]
                                porcentagem = round((count / len(df_filtrado)) * 100, 2)
                                
                                dados_turno.append({
                                    "Turno": info_turno['nome'],
                                    "Quantidade": int(count),
                                    "Intervalo": info_turno['intervalo'],
                                    "Porcentagem": porcentagem
                                })
                                
                                print(f"   {info_turno['nome']}: {count} ({porcentagem}%)")
                        
                        if not dados_turno:
                            resultados[nome] = {
                                "erro": "Nenhuma transação encontrada",
                                "sucesso": False,
                            }
                            print(f"❌ Sem dados para comparar")
                            continue

                        print(f"\n✅ Comparação por turno gerada com sucesso")
                        print(f"   Total de transações: {len(df_filtrado)}")
                        print(f"   Turnos com dados: {len(dados_turno)}")
                        
                        resultados[nome] = {
                            "filter_column": filter_column,
                            "filter_value": filter_value,
                            "total_transacoes": int(len(df_filtrado)),
                            "dados_turno": dados_turno,  # ← Lista de dicts pronta para gráfico
                            "arquivo_local": arquivo_info["arquivo_local"],
                            "sucesso": True,
                        }
                        
                    except Exception as e:
                        error_msg = f"Erro ao comparar por turno: {str(e)}"
                        print(f"❌ {error_msg}")
                        resultados[nome] = {
                            "erro": error_msg,
                            "traceback": traceback.format_exc(),
                            "sucesso": False,
                        }

                elif operation == "leitura_tarifa": 
                    consulta_tipo = params.get("consulta_tipo", "atual")
                    ano = params.get("ano")
                    
                    print(f"\n💰 LEITURA_TARIFA_METRO:")
                    print(f"   Consulta: {consulta_tipo}")
                    if ano:
                        print(f"   Ano: {ano}")
                    
                    resultados[nome] = executar_leitura_tarifa(
                        df=df,
                        consulta_tipo=consulta_tipo,
                        ano=ano,
                        arquivo_local=arquivo_info["arquivo_local"]
                    )

                elif operation in ["media", "soma", "max", "min"]:
                    resultados[nome] = executar_estatistica(df, operation, arquivo_info["arquivo_local"])

                elif operation == "contar_por_turno":
                    filter_column = params.get("filter_column")
                    filter_value = params.get("filter_value")
                    data_coluna = params.get("data_coluna", "Data da Transação")

                    print(f"\n🕐 CONTAR_POR_TURNO:")
                    print(f"   Coluna de filtro: {filter_column}")
                    print(f"   Valor de filtro: {filter_value}")
                    print(f"   Coluna de data: {data_coluna}")

                    if not filter_column or filter_value is None:
                        resultados[nome] = {
                            "erro": "Parâmetros 'filter_column' e 'filter_value' são obrigatórios",
                            "sucesso": False,
                        }
                        print(f"❌ Parâmetros faltando")
                        continue

                    if data_coluna not in df.columns:
                        resultados[nome] = {
                            "erro": f"Coluna de data '{data_coluna}' não encontrada",
                            "colunas_disponiveis": list(df.columns),
                            "sucesso": False,
                        }
                        print(f"❌ Coluna '{data_coluna}' não existe")
                        continue

                    try:
                        df[data_coluna] = pd.to_datetime(df[data_coluna], errors='coerce')
                        
                        df['_hora_extraida'] = df[data_coluna].dt.hour
                        df['_minuto_extraido'] = df[data_coluna].dt.minute
                        df['_faixa_horaria'] = df.apply(
                            lambda row: _determinar_faixa_horaria(row['_hora_extraida'], row['_minuto_extraido']),
                            axis=1
                        )
                        df_filtrado = df[
                            df[filter_column].astype(str).str.contains(str(filter_value), case=False, na=False)
                        ]
                        
                        total_linhas = len(df_filtrado)
                        print(f"✅ Filtrado: {total_linhas} linhas com '{filter_value}'")

                        if total_linhas == 0:
                            resultados[nome] = {
                                "erro": f"Nenhuma transação encontrada para '{filter_value}'",
                                "sucesso": False,
                            }
                            print(f"❌ Nenhuma linha encontrada")
                        else:
                            contagem_por_turno = {}
                            turno_com_mais = None
                            max_count = 0

                            for t in range(4):
                                count = len(df_filtrado[df_filtrado['_faixa_horaria'] == t])
                                info_turno = FAIXAS_HORARIAS[t]
                                
                                if count > 0:
                                    contagem_por_turno[info_turno['nome']] = {
                                        "quantidade": int(count),
                                        "intervalo": info_turno['intervalo'],
                                        "porcentagem": round((count / total_linhas) * 100, 2)
                                    }
                                    
                                    if count > max_count:
                                        max_count = count
                                        turno_com_mais = info_turno['nome']

                            print(f"\n📊 Distribuição por turno:")
                            for turno_nome, dados in contagem_por_turno.items():
                                print(f"   {turno_nome}: {dados['quantidade']} ({dados['porcentagem']}%)")

                            resultados[nome] = {
                                "filter_column": filter_column,
                                "filter_value": filter_value,
                                "total_transacoes": int(total_linhas),
                                "contagem_por_turno": contagem_por_turno,
                                "turno_com_mais_uso": turno_com_mais,
                                "turno_com_mais_uso_quantidade": int(max_count),
                                "resumo": f"🏆 {turno_com_mais} teve o maior uso ({max_count} transações, {contagem_por_turno[turno_com_mais]['porcentagem']}%)",
                                "arquivo_local": arquivo_info["arquivo_local"],
                                "sucesso": True,
                            }

                    except Exception as e:
                        error_msg = f"Erro ao contar por turno: {str(e)}"
                        print(f"❌ {error_msg}")
                        resultados[nome] = {
                            "erro": error_msg,
                            "traceback": traceback.format_exc(),
                            "sucesso": False,
                        }
                else:
                    resultados[nome] = {
                        "erro": f"Operação desconhecida: {operation}",
                        "operacoes_disponiveis": [
                            "contar_linhas", "mostrar_colunas", "preview",
                            "contar_por_valor", "agrupar_e_somar",
                            "media", "soma", "max", "min"
                        ],
                        "sucesso": False,
                    }
                    print(f"❌ Operação '{operation}' não reconhecida")

                arquivos_analisados += 1
                print(f"\n✅ Operação '{operation}' concluída com sucesso")
                print("="*80)

            except Exception as e:
                error_msg = f"Erro ao analisar arquivo {arquivo_info.get('nome', 'desconhecido')}: {str(e)}"
                print(f"\n❌ DEBUG - {error_msg}")
                print(f"❌ DEBUG - Traceback: {traceback.format_exc()}")
                resultados[arquivo_info.get("nome", "desconhecido")] = {
                    "erro": error_msg,
                    "traceback": traceback.format_exc(),
                    "sucesso": False,
                }

        try:
            resultados["_resumo_analise"] = {
                "pasta_temporaria": obter_pasta_temporaria(),
                "arquivos_analisados": arquivos_analisados,
                "operacao_executada": operation,
                "sucesso_geral": arquivos_analisados > 0,
            }
            
            print(f"\n{'='*80}")
            print(f"📊 RESUMO: {arquivos_analisados} arquivo(s) analisado(s)")
            print("="*80)
            
        except Exception as e:
            print(f"❌ DEBUG - Erro ao gerar resumo: {str(e)}")

        return resultados

    except Exception as e:
        error_msg = f"Falha geral na análise: {str(e)}"
        full_tb = traceback.format_exc()
        print(f"\n❌ DEBUG - {error_msg}")
        print(f"❌ DEBUG - Traceback: {full_tb}")
        return {
            "erro": error_msg,
            "traceback_completo": full_tb,
            "sucesso": False,
        }
    
