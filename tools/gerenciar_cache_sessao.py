import os
import shutil
from typing import Any
from langchain.tools import tool

@tool("gerenciar_cache_sessao")
def gerenciar_cache_sessao(params: dict) -> Any:
    """
    Gerencia arquivos baixados na pasta temporária da sessão.
    
    Parâmetros esperados em *params*:
    - acao (str): listar | limpar | info | remover_arquivo
    - arquivo (str): nome do arquivo específico (para acao=remover_arquivo)
    """
    
    try:
        acao = params.get("acao", "listar")
        arquivo_especifico = params.get("arquivo")
        
        try:
            from tools.baixar_arquivo_dados import obter_pasta_temporaria, limpar_pasta_temporaria_manual
        except ImportError:
            return {"erro": "Módulo de gerenciamento de pasta temporária não disponível"}
        
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
                "acoes_disponiveis": ["listar", "info", "limpar", "remover_arquivo"],
                "sucesso": False
            }

    except Exception as e:
        return {
            "erro": f"Erro no gerenciamento de cache: {str(e)}",
            "sucesso": False
        }