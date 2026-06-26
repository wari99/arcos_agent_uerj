import os
import shutil
from typing import Any, Dict, List
from langchain.tools import tool

from tools.baixar_arquivo_dados import obter_pasta_temporaria, obter_cache_arquivos, baixar_arquivo_dados
import traceback

def limpar_pasta_temporaria_manual() -> Dict:
    """
    Limpa pasta temporária e cache. Remove a pasta temporária que foi criada durante a sessão e limpa o dicionário em cache. 

    Returns:
        Dict com as chaves:
        - status (str): "sucesso", "info" ou "erro"
        - mensagem (str): Descrição do resultado da operação

    """
    from tools.baixar_arquivo_dados import _pasta_temporaria_global, _cache_arquivos #vars globais
    
    print(f" DEBUG: _pasta_temporaria_global = {_pasta_temporaria_global}")
    print(f" DEBUG: Existe? {os.path.exists(_pasta_temporaria_global) if _pasta_temporaria_global else False}")
    
    if not (_pasta_temporaria_global and os.path.exists(_pasta_temporaria_global)):
        print(" Sem pasta para limpar")
        return {
            "status": "info", 
            "mensagem": "Nenhuma pasta temporária para remover"
        }
    
    try:
        print(f"🗑️ Removendo: {_pasta_temporaria_global}")
        shutil.rmtree(_pasta_temporaria_global)
        print(f"✅ Pasta removida: {_pasta_temporaria_global}")
        
        _pasta_temporaria_global = None
        _cache_arquivos.clear()
        print("🧹 Cache limpo")
        
        return {
            "status": "sucesso", 
            "mensagem": "Pasta e cache removidos"
        }
    except Exception as e:
        print(f"❌ Erro: {e}")
        return {
            "status": "erro", 
            "mensagem": f"Erro ao remover: {e}"
        }

def obter_arquivos_para_analise(
    package_id: str,
    file_filter: str = "",
    força_download: bool = False
) -> Dict[str, Any]:
    """
    Obtém arquivos prontos para análise.
    
    Centraliza toda a lógica de obtenção dos dados:
    - Tenta obter um arquivo o cache local
    - Se não encontra o arquivo, baixa-o através do endpoint da API de Dados Abertos
    - Valida e retorna os arquivos prontos para uso
    
    Args:
        package_id (str): ID do package na API
        file_filter (str): Filtro para selecionar apenas arquivos que contenham determinado texto no nome. Case-insensitive 
        força_download (bool, Optional): Se for True, ignora o cache e força um novo download duplicado. 
                                        O default de força_download é False.
    
    Returns:
        {
            "arquivos": [{"nome": "...", "df": ..., "arquivo_local": "...", "do_cache": bool}],
            "total_arquivos": int,
            "do_cache": bool,
            "erro": str (se houver),
            "sucesso": bool
        }
    """
    
    try:
        print(f"\n* OBTER_ARQUIVOS_PARA_ANALISE:")
        print(f"   Package ID: {package_id}")
        print(f"   Filtro: {file_filter if file_filter else '(nenhum)'}")
        print(f"   Força download: {força_download}")
        
        arquivos_para_analisar: List[Dict] = []
        
        if not força_download:
            print(f"\n   📦 Procurando no cache...")
            
            try:
                cache_arquivos = obter_cache_arquivos()
                print(f"   ✅ Cache obtido: {len(cache_arquivos)} arquivos")
                
                for info_cache in cache_arquivos.values():
                    nome_arquivo = info_cache.get("nome", "")
                    
                    if file_filter and file_filter.lower() not in nome_arquivo.lower():
                        continue
                    
                    if os.path.exists(info_cache["arquivo_local"]):
                        arquivos_para_analisar.append({
                            "nome": nome_arquivo,
                            "df": info_cache["dataframe"],
                            "arquivo_local": info_cache["arquivo_local"],
                            "do_cache": True,
                        })
                        print(f"   ✅ {nome_arquivo} (do cache)")
                
                if arquivos_para_analisar:
                    print(f"   ✅ {len(arquivos_para_analisar)} arquivo(s) encontrado(s) no cache!")
                    return {
                        "arquivos": arquivos_para_analisar,
                        "total_arquivos": len(arquivos_para_analisar),
                        "do_cache": True,
                        "sucesso": True
                    }
                
                print(f"   ⚠️ Nenhum arquivo no cache, baixando...")
                
            except Exception as e:
                print(f"   ⚠️ Erro ao acessar cache: {e}")
                print(f"   ⚠️ Tentando download mesmo assim...")
        

        print(f"\n   📥 Baixando arquivo(s)...")
        try:
            resultado_download = baixar_arquivo_dados.func({
                "package_id": package_id,
                "file_filter": file_filter,
            })
            
            print(f"   ✅ Download concluído")
            
        except Exception as e:
            error_msg = f"Erro durante download: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "erro": error_msg,
                "sucesso": False,
                "traceback": traceback.format_exc()
            }
        
        if not isinstance(resultado_download, dict) or "erro" in resultado_download:
            erro_msg = (
                resultado_download.get("erro", "Erro desconhecido")
                if isinstance(resultado_download, dict)
                else "Resposta inválida"
            )
            print(f"   ❌ Erro no download: {erro_msg}")
            return {
                "erro": f"Falha no download: {erro_msg}",
                "sucesso": False
            }
        

        print(f"\n    Atualizando cache...") 
        try:
            cache_arquivos = obter_cache_arquivos()
            print(f"   ✅ Cache atualizado: {len(cache_arquivos)} arquivos")
            
            for nome, info in resultado_download.items():
                if nome == "_resumo_processamento":
                    continue
                if not isinstance(info, dict) or not info.get("sucesso"):
                    continue
                
                for info_cache in cache_arquivos.values():
                    if info_cache["nome"] == nome:
                        if os.path.exists(info_cache["arquivo_local"]):
                            arquivos_para_analisar.append({
                                "nome": nome,
                                "df": info_cache["dataframe"],
                                "arquivo_local": info_cache["arquivo_local"],
                                "do_cache": False,  
                            })
                            print(f"   ✅ {nome} (baixado)")
                        break
            
        except Exception as e:
            error_msg = f"Erro ao processar cache após download: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "erro": error_msg,
                "sucesso": False,
                "traceback": traceback.format_exc()
            }

        if not arquivos_para_analisar:
            print(f"   ❌ Nenhum arquivo disponível após download")
            return {
                "erro": "Nenhum arquivo disponível para análise",
                "detalhes": f"package_id={package_id}, file_filter='{file_filter}'",
                "sucesso": False
            }
        
        print(f"\n   ✅ {len(arquivos_para_analisar)} arquivo(s) pronto(s) para análise!")
        
        return {
            "arquivos": arquivos_para_analisar,
            "total_arquivos": len(arquivos_para_analisar),
            "do_cache": False, 
            "sucesso": True
        }
        
    except Exception as e:
        error_msg = f"Erro crítico em obter_arquivos_para_analise: {str(e)}"
        print(f"   ❌ {error_msg}")
        return {
            "erro": error_msg,
            "traceback": traceback.format_exc(),
            "sucesso": False
        }


@tool("gerenciar_cache_sessao")
def gerenciar_cache_sessao(params: dict) -> Any:
    """
    Gerencia os arquivos baixados na pasta temporária da sessão.

    Oferece ações para listar, verificar, limpar e remover arquivos da pasta temporária da sessão;

    Args:
        params (dict): Dicionário com parâmetros da ação:
            Sempre obrigatório:
                - acao (str): Tipo de operação a realizar
            
            Ações disponíveis:
                "listar": Lista todos os arquivos da pasta temporária.
                    Retorna: lista de arquivos com nome, tamanho e caminho

                "info": Obtém informações resumidas do cache.
                    Retorna: total de arquivos e tamanho total em MB
                
                "limpar": Remove completamente a pasta temporária e cache.
                
                "remover_arquivo": Remove um arquivo específico do cache.
                    Parâmetro: arquivo (str) - nome do arquivo
                
                "obter_para_analise": Através de parametros passados, valida e chama a função obter_arquivos_para_analise().
                                    Procura em cache o arquivo desejado, baixa do servidor caso não encontre. Valida download
                                    e valida o cache atual, retornando o resultado.
                    Parâmetros:
                        - package_id (str, obrigatório): ID da base
                        - file_filter (str, opcional): Filtro de nome
                        - força_download (bool, opcional): Força novo download
    """
    
    try:
        acao = params.get("acao", "listar")
        if acao == "obter_para_analise":
            package_id = params.get("package_id")
            file_filter = params.get("file_filter", "")
            força_download = params.get("força_download", False)
            
            if not package_id:
                return {
                    "erro": "Parâmetro 'package_id' é obrigatório",
                    "sucesso": False
                }
            
            return obter_arquivos_para_analise(
                package_id=package_id,
                file_filter=file_filter,
                força_download=força_download
            )
                
        pasta_temp = obter_pasta_temporaria()
        
        if not pasta_temp or not os.path.exists(pasta_temp):
            return {
                "acao": acao,
                "status": "info",
                "mensagem": "Nenhuma pasta temporária ativa"
            }

        if acao == "listar":
            arquivos = []
            total_tamanho = 0
            
            for item in os.listdir(pasta_temp):
                caminho_completo = os.path.join(pasta_temp, item)
                if os.path.isfile(caminho_completo):
                    tamanho = os.path.getsize(caminho_completo)
                    total_tamanho += tamanho
                    
                    arquivos.append({
                        "nome": item,
                        "tamanho_bytes": tamanho,
                        "tamanho_mb": round(tamanho / (1024*1024), 2),
                        "caminho_completo": caminho_completo
                    })
            
            return {
                "acao": "listar",
                "pasta_temporaria": pasta_temp,
                "total_arquivos": len(arquivos),
                "total_tamanho_mb": round(total_tamanho / (1024*1024), 2),
                "arquivos": arquivos,
                "sucesso": True
            }

        elif acao == "info":
            if not os.path.exists(pasta_temp):
                return {
                    "acao": "info",
                    "status": "pasta_inexistente",
                    "mensagem": "Pasta temporária não existe"
                }
            
            total_arquivos = 0
            total_tamanho = 0
            
            for item in os.listdir(pasta_temp):
                caminho_completo = os.path.join(pasta_temp, item)
                if os.path.isfile(caminho_completo):
                    total_arquivos += 1
                    total_tamanho += os.path.getsize(caminho_completo)
            
            return {
                "acao": "info",
                "pasta_temporaria": pasta_temp,
                "total_arquivos": total_arquivos,
                "total_tamanho_mb": round(total_tamanho / (1024*1024), 2),
                "pasta_existe": True,
                "sucesso": True
            }

        elif acao == "limpar":
            resultado_limpeza = limpar_pasta_temporaria_manual()
            return {
                "acao": "limpar",
                "resultado": resultado_limpeza,
                "sucesso": resultado_limpeza.get("status") == "sucesso"
            }

        elif acao == "remover_arquivo":
            arquivo_especifico = params.get("arquivo")
            
            if not arquivo_especifico:
                return {
                    "acao": "remover_arquivo",
                    "erro": "É necessário especificar o nome do arquivo",
                    "sucesso": False
                }
            
            caminho_arquivo = os.path.join(pasta_temp, arquivo_especifico)
            
            if not os.path.exists(caminho_arquivo):
                return {
                    "acao": "remover_arquivo",
                    "arquivo": arquivo_especifico,
                    "erro": "Arquivo não encontrado",
                    "sucesso": False
                }
            
            try:
                os.remove(caminho_arquivo)
                return {
                    "acao": "remover_arquivo",
                    "arquivo": arquivo_especifico,
                    "mensagem": f"Arquivo '{arquivo_especifico}' removido com sucesso",
                    "sucesso": True
                }
            except Exception as e:
                return {
                    "acao": "remover_arquivo",
                    "arquivo": arquivo_especifico,
                    "erro": f"Erro ao remover arquivo: {str(e)}",
                    "sucesso": False
                }

        else:
            return {
                "erro": f"Ação desconhecida: {acao}",
                "acoes_disponiveis": ["listar", "info", "limpar", "remover_arquivo", "obter_para_analise"],
                "sucesso": False
            }

    except Exception as e:
        return {
            "erro": f"Erro no gerenciamento de cache: {str(e)}",
            "sucesso": False
        }
    