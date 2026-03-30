import os
import traceback
from typing import Any, Dict, List
import pandas as pd
from langchain.tools import tool

from tools.baixar_arquivo_dados import (
    obter_cache_arquivos,
    obter_pasta_temporaria,
    listar_cache_arquivos,
    baixar_arquivo_dados,
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
      
      Para 'contar_por_valor':
      - column: coluna para filtrar (ex: "TIPO_GRATUIDADE")
      - value: valor a buscar (ex: "Idoso")
      
      Para 'agrupar_e_somar':
      - filter_column: coluna para filtrar (ex: "TIPO_GRATUIDADE")
      - filter_value: valor a filtrar (ex: "Idoso")
      - sum_column: coluna numérica para somar (ex: "QUANTIDADE_TRANSACAO")
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
        
        if operation == "agrupar_e_somar":
            print(f"   filter_column: {params.get('filter_column')}")
            print(f"   filter_value: {params.get('filter_value')}")
            print(f"   sum_column: {params.get('sum_column')}")
        elif operation == "contar_por_valor":
            print(f"   column: {params.get('column')}")
            print(f"   value: {params.get('value')}")
        
        print("="*80)

        if not package_id:
            return {
                "erro": "Parâmetro 'package_id' é obrigatório para análise.",
                "sucesso": False,
            }

        print(f"🔍 Analisando arquivos na base '{package_id}' com filtro '{file_filter}'")
        print(f"📊 Operação solicitada: {operation}")

        try:
            cache_arquivos = obter_cache_arquivos()
            print(f"✅ DEBUG - Cache obtido com {len(cache_arquivos)} arquivos")
        except Exception as e:
            error_msg = f"Erro ao obter cache: {str(e)}"
            print(f"❌ DEBUG - {error_msg}")
            return {"erro": error_msg, "sucesso": False}

        arquivos_para_analisar: List[Dict] = []

        print(f"\n🔍 Verificando cache... {len(cache_arquivos)} arquivos disponíveis")

        for chave, info_cache in cache_arquivos.items():
            nome_arquivo = info_cache.get("nome", "")
            print(f"   📄 Verificando: {nome_arquivo}")

            if file_filter:
                if file_filter.lower() not in nome_arquivo.lower():
                    print(f"      ❌ Não corresponde ao filtro '{file_filter}'")
                    continue
                else:
                    print(f"      ✅ Corresponde ao filtro!")

            if os.path.exists(info_cache["arquivo_local"]):
                arquivos_para_analisar.append(
                    {
                        "nome": info_cache["nome"],
                        "df": info_cache["dataframe"],
                        "arquivo_local": info_cache["arquivo_local"],
                        "do_cache": True,
                    }
                )
                print(f"      ♻️ Adicionado para análise (do cache)")

        if not arquivos_para_analisar:
            print("\n📥 DEBUG - Nenhum arquivo no cache - baixando primeiro...")

            try:
                resultado_download = baixar_arquivo_dados.func(
                    {
                        "package_id": package_id,
                        "file_filter": file_filter,
                    }
                )

                print(f"✅ DEBUG - Download executado")

            except Exception as e:
                error_msg = f"Erro durante download: {str(e)}"
                print(f"❌ DEBUG - {error_msg}")
                return {
                    "erro": error_msg,
                    "sucesso": False,
                    "traceback": traceback.format_exc(),
                }

            if not isinstance(resultado_download, dict) or "erro" in resultado_download:
                erro_msg = (
                    resultado_download.get("erro", "Erro desconhecido no download")
                    if isinstance(resultado_download, dict)
                    else "Resposta inválida da função de download"
                )
                print(f"❌ DEBUG - Erro no download: {erro_msg}")
                return {
                    "erro": f"Falha no download do arquivo: {erro_msg}",
                    "detalhes": f"package_id={package_id}, file_filter='{file_filter}'",
                    "sucesso": False,
                }

            try:
                cache_arquivos = obter_cache_arquivos()
                print(f"✅ DEBUG - Cache atualizado com {len(cache_arquivos)} arquivos")

                for nome, info in resultado_download.items():
                    if nome == "_resumo_processamento":
                        continue
                    if not isinstance(info, dict):
                        continue
                    if not info.get("sucesso"):
                        continue

                    for chave, info_cache in cache_arquivos.items():
                        if info_cache["nome"] == nome and os.path.exists(
                            info_cache["arquivo_local"]
                        ):
                            arquivos_para_analisar.append(
                                {
                                    "nome": nome,
                                    "df": info_cache["dataframe"],
                                    "arquivo_local": info_cache["arquivo_local"],
                                    "do_cache": info.get("do_cache", False),
                                }
                            )
                            print(f"✅ DEBUG - Arquivo adicionado após download: {nome}")
                            break

            except Exception as e:
                error_msg = f"Erro ao processar cache após download: {str(e)}"
                print(f"❌ DEBUG - {error_msg}")
                return {
                    "erro": error_msg,
                    "sucesso": False,
                    "traceback": traceback.format_exc(),
                }

        if not arquivos_para_analisar:
            print("❌ DEBUG - Nenhum arquivo disponível para análise")
            return {
                "erro": "Nenhum arquivo disponível para análise",
                "detalhes": f"package_id={package_id}, file_filter='{file_filter}'",
                "cache_disponivel": len(cache_arquivos),
                "sucesso": False,
            }

        print(f"\n✅ DEBUG - Total de arquivos para analisar: {len(arquivos_para_analisar)}")

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
                    memoria_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
                    resultados[nome] = {
                        "linhas": len(df),
                        "colunas": len(df.columns),
                        "nomes_colunas": list(df.columns),
                        "memoria_mb": round(memoria_mb, 2),
                        "arquivo_local": arquivo_info["arquivo_local"],
                        "sucesso": True,
                    }
                    print(f"✅ Contagem: {len(df)} linhas")

                elif operation == "mostrar_colunas":
                    resultados[nome] = {
                        "colunas": list(df.columns),
                        "total_colunas": len(df.columns),
                        "linhas": len(df),
                        "tipos": df.dtypes.astype(str).to_dict(),
                        "arquivo_local": arquivo_info["arquivo_local"],
                        "sucesso": True,
                    }
                    print(f"✅ Colunas listadas: {len(df.columns)}")

                elif operation == "preview":
                    print(f"📋 Gerando preview...")
                    preview_data = df.head().to_dict("records")
                    print(f"✅ Preview gerado com {len(preview_data)} linhas")
                    print(f"\n📄 PRIMEIRAS LINHAS:")
                    for i, row in enumerate(preview_data, 1):
                        print(f"   Linha {i}: {row}")
                    
                    resultados[nome] = {
                        "primeiras_5_linhas": preview_data,
                        "colunas": list(df.columns),
                        "total_linhas": len(df),
                        "total_colunas": len(df.columns),
                        "arquivo_local": arquivo_info["arquivo_local"],
                        "sucesso": True,
                    }

                elif operation == "contar_por_valor":
                    coluna = params.get("column")
                    valor = params.get("value")

                    print(f"\n🔍 CONTAR_POR_VALOR (conta linhas):")
                    print(f"   Coluna: {coluna}")
                    print(f"   Valor procurado: {valor}")

                    if not coluna or valor is None:
                        resultados[nome] = {
                            "erro": "Parâmetros 'column' e 'value' são obrigatórios",
                            "sucesso": False,
                        }
                        print(f"❌ Parâmetros faltando")
                    elif coluna not in df.columns:
                        resultados[nome] = {
                            "erro": f"Coluna '{coluna}' não encontrada",
                            "colunas_disponiveis": list(df.columns),
                            "sucesso": False,
                        }
                        print(f"❌ Coluna '{coluna}' não existe")
                    else:
                        df_filtrado = df[df[coluna] == valor]
                        total_linhas = len(df_filtrado)
                        
                        print(f"\n   🔢 RESULTADO: {total_linhas} linhas encontradas")
                        
                        resultados[nome] = {
                            "coluna": coluna,
                            "valor": valor,
                            "total_linhas": int(total_linhas),
                            "arquivo_local": arquivo_info["arquivo_local"],
                            "sucesso": True,
                        }

                elif operation == "agrupar_e_somar":
                    filter_column = params.get("filter_column")
                    filter_value = params.get("filter_value")
                    sum_column = params.get("sum_column")

                    print(f"\n🔍 AGRUPAR_E_SOMAR:")
                    print(f"   Filtrar coluna: {filter_column}")
                    print(f"   Filtrar valor: {filter_value}")
                    print(f"   Somar coluna: {sum_column}")

                    if not filter_column or filter_value is None:
                        resultados[nome] = {
                            "erro": "Parâmetros 'filter_column' e 'filter_value' são obrigatórios",
                            "sucesso": False,
                        }
                        print(f"❌ Parâmetros de filtro faltando")
                    elif not sum_column:
                        resultados[nome] = {
                            "erro": "Parâmetro 'sum_column' é obrigatório",
                            "exemplo": "sum_column='QUANTIDADE_TRANSACAO'",
                            "sucesso": False,
                        }
                        print(f"❌ Falta sum_column")
                    elif filter_column not in df.columns:
                        resultados[nome] = {
                            "erro": f"Coluna de filtro '{filter_column}' não encontrada",
                            "colunas_disponiveis": list(df.columns),
                            "sucesso": False,
                        }
                        print(f"❌ Coluna '{filter_column}' não existe")
                    elif sum_column not in df.columns:
                        resultados[nome] = {
                            "erro": f"Coluna a somar '{sum_column}' não encontrada",
                            "colunas_disponiveis": list(df.columns),
                            "sucesso": False,
                        }
                        print(f"❌ Coluna '{sum_column}' não existe")
                    else:
                        valores_unicos = df[filter_column].unique()
                        print(f"\n   📊 Valores únicos em '{filter_column}': {list(valores_unicos)[:10]}")
                        
                        df_filtrado = df[df[filter_column] == filter_value]
                        total_linhas = len(df_filtrado)
                        
                        print(f"\n   📊 Linhas filtradas: {total_linhas}")
                        
                        if total_linhas == 0:
                            print(f"   ⚠️ NENHUMA linha corresponde ao valor '{filter_value}'")
                            print(f"   Valores disponíveis: {list(valores_unicos)[:10]}")
                            
                            resultados[nome] = {
                                "filter_column": filter_column,
                                "filter_value": filter_value,
                                "sum_column": sum_column,
                                "total_linhas": 0,
                                "soma_total": 0,
                                "valores_disponiveis": list(valores_unicos),
                                "sucesso": True,
                            }
                        else:
                            if sum_column in df_filtrado.select_dtypes(include=["number"]).columns:
                                soma_total = df_filtrado[sum_column].sum()
                                print(f"   ✅ Soma de '{sum_column}': {soma_total:,.0f}")
                                print(f"\n   Primeiras linhas filtradas:")
                                print(df_filtrado[[filter_column, sum_column]].head())
                                
                                resultados[nome] = {
                                    "filter_column": filter_column,
                                    "filter_value": filter_value,
                                    "sum_column": sum_column,
                                    "total_linhas": int(total_linhas),
                                    "soma_total": float(soma_total),
                                    "arquivo_local": arquivo_info["arquivo_local"],
                                    "sucesso": True,
                                }
                            else:
                                print(f"   ❌ Coluna '{sum_column}' não é numérica")
                                resultados[nome] = {
                                    "erro": f"Coluna '{sum_column}' não é numérica",
                                    "tipo_coluna": str(df[sum_column].dtype),
                                    "sucesso": False,
                                }

                elif operation in ["media", "soma", "max", "min"]:
                    numericas = df.select_dtypes(include=["number"])
                    print(f"\n📊 Operação: {operation}")
                    print(f"   Colunas numéricas: {list(numericas.columns)}")
                    
                    if numericas.empty:
                        resultados[nome] = {
                            "erro": "Nenhuma coluna numérica encontrada",
                            "sucesso": False,
                        }
                        print(f"❌ Nenhuma coluna numérica")
                    else:
                        if operation == "media":
                            res = numericas.mean().to_dict()
                        elif operation == "soma":
                            res = numericas.sum().to_dict()
                        elif operation == "max":
                            res = numericas.max().to_dict()
                        else:  # operacao: minimo
                            res = numericas.min().to_dict()

                        print(f"✅ Resultado: {res}")
                        
                        resultados[nome] = {
                            "resultado": res,
                            "colunas_analisadas": list(numericas.columns),
                            "arquivo_local": arquivo_info["arquivo_local"],
                            "sucesso": True,
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