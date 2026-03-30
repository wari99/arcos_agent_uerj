import os
import io
import zipfile
import tempfile
import requests
import pandas as pd
import shutil
import hashlib
from typing import Any, Dict, Optional
from langchain.tools import tool

_pasta_temporaria_global = None #Pasta temporária única por sessão do agente, mantida até ser digitado /sair
_cache_arquivos: Dict[str, Dict] = {} #Cache dos downloads, evitar downloads repetidos.

def _criar_pasta_temporaria():
    """
    Cria pasta temporária única para a sessão
    """
    global _pasta_temporaria_global
    
    if _pasta_temporaria_global is None or not os.path.exists(_pasta_temporaria_global):
        _pasta_temporaria_global = tempfile.mkdtemp(prefix="arcos_rj_")
        print(f"📂 Nova pasta temporária criada: {_pasta_temporaria_global}")
    
    return _pasta_temporaria_global

def _gerar_chave_cache(url_arquivo: str, nome_arquivo: str) -> str:
    """
    Gera uma chave única para o cache baseada na URL e nome do arquivo
    """
    conteudo = f"{url_arquivo}|{nome_arquivo}"
    return hashlib.md5(conteudo.encode()).hexdigest()[:16]

def _arquivo_existe_no_cache(chave_cache: str) -> Optional[Dict]:
    """
    Verifica se arquivo já foi baixado e ainda existe na pasta
    """
    global _cache_arquivos
    
    if chave_cache not in _cache_arquivos:
        return None
    
    info_cache = _cache_arquivos[chave_cache]
    arquivo_local = info_cache.get("arquivo_local")
    
    if arquivo_local and os.path.exists(arquivo_local):
        print(f"🔄 Arquivo encontrado no cache: {os.path.basename(arquivo_local)}")
        return info_cache
    else:
        del _cache_arquivos[chave_cache]
        return None

def _salvar_no_cache(chave_cache: str, info_arquivo: Dict):
    """
    Salva informações do arquivo no cache
    """
    global _cache_arquivos
    _cache_arquivos[chave_cache] = info_arquivo
    print(f"💾 Arquivo salvo no cache: {info_arquivo['nome']}")

def _baixar_e_processar_arquivo(resource: Dict, pasta_temp: str) -> Dict:
    """
    Baixa arquivo (se necessário) e retorna DataFrame processado
    """
    url_arquivo = resource.get("url")
    nome = resource.get("name", "arquivo_sem_nome")
    mimetype = (resource.get("mimetype") or "").lower()
    
    chave_cache = _gerar_chave_cache(url_arquivo, nome)
    cache_info = _arquivo_existe_no_cache(chave_cache)
    
    if cache_info:
        print(f"♻️ Reutilizando arquivo encontrado em cache: {nome}")
        return {
            "df": cache_info["dataframe"],
            "nome": nome,
            "arquivo_local": cache_info["arquivo_local"],
            "do_cache": True,
            "sucesso": True
        }
    
    print(f"\n⬇️ Baixando novo arquivo: {nome}")
    print(f"📡 URL: {url_arquivo}")
    
    try:
        response = requests.get(url_arquivo, timeout=60, stream=True)
        response.raise_for_status()
        
        arquivo_local = os.path.join(pasta_temp, nome)
        with open(arquivo_local, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Arquivo salvo: {arquivo_local}")
        
        df = None
        is_zip = "zip" in mimetype or nome.lower().endswith(".zip")

        if is_zip:
            print("📦 Arquivo ZIP detectado - extraindo CSV...")
            try:
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    csv_files = [f for f in zip_ref.namelist() if f.lower().endswith(".csv")]

                    if not csv_files:
                        return {"erro": "ZIP não contém arquivos CSV", "sucesso": False}

                    csv_file = csv_files[0]
                    print(f"📄 Extraindo: {csv_file}")
                    
                    with zip_ref.open(csv_file) as f:
                        content = f.read().decode('utf-8', errors='replace')
                        
                        if content[:2000].count(';') > content[:2000].count(','):
                            df = pd.read_csv(io.StringIO(content), sep=";")
                            print("🇧🇷 Usando separador brasileiro (;)")
                        else:
                            df = pd.read_csv(io.StringIO(content), sep=",")
                            print("🌍 Usando separador internacional (,)")
                            
            except zipfile.BadZipFile:
                return {"erro": "Arquivo ZIP corrompido", "sucesso": False}
            except Exception as e:
                return {"erro": f"Erro ao processar ZIP: {str(e)}", "sucesso": False}
        else:
            print("📄 Arquivo CSV direto - processando...")
            try:
                try:
                    content = response.content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = response.content.decode('latin-1')
                        print("🔄 Usando encoding Latin-1")
                    except UnicodeDecodeError:
                        content = response.content.decode('utf-8', errors='replace')
                        print("⚠️ Usando UTF-8 com substituição de caracteres")
                
                amostra = content[:2000] 
                count_semicolon = amostra.count(';')
                count_comma = amostra.count(',')
                
                if count_semicolon > count_comma and count_semicolon > 10:
                    df = pd.read_csv(io.StringIO(content), sep=";")
                    print("🇧🇷 Detectado separador brasileiro (;)")
                elif count_comma > 10:
                    df = pd.read_csv(io.StringIO(content), sep=",")
                    print("🌍 Detectado separador internacional (,)")
                else:
                    try:
                        df = pd.read_csv(io.StringIO(content), sep=";")
                        print("🤞 Tentativa com separador (;)")
                    except:
                        df = pd.read_csv(io.StringIO(content), sep=",")
                        print("🤞 Tentativa com separador (,)")
                        
            except Exception as e:
                return {"erro": f"Erro ao processar CSV: {str(e)}", "sucesso": False}

        if df is None or df.empty:
            return {"erro": "Não foi possível criar DataFrame ou arquivo vazio", "sucesso": False}

        print(f"✅ DataFrame criado: {len(df)} linhas, {len(df.columns)} colunas")
        
        info_cache = {
            "nome": nome,
            "arquivo_local": arquivo_local,
            "dataframe": df,
            "url_original": url_arquivo,
            "tamanho_mb": round(len(response.content) / (1024*1024), 2),
            "linhas": len(df),
            "colunas": len(df.columns)
        }
        
        _salvar_no_cache(chave_cache, info_cache)
        
        return {
            "df": df,
            "nome": nome,
            "arquivo_local": arquivo_local,
            "do_cache": False,
            "sucesso": True
        }
        
    except requests.exceptions.Timeout:
        return {"erro": "Timeout ao baixar arquivo (60s)", "sucesso": False}
    except requests.exceptions.RequestException as e:
        return {"erro": f"Erro de rede: {str(e)}", "sucesso": False}
    except Exception as e:
        return {"erro": f"Erro inesperado: {str(e)}", "sucesso": False}

def limpar_pasta_temporaria_manual():
    """
    Função para limpar pasta temporária manualmente (chamada pelo comando /sair)
    """
    global _pasta_temporaria_global, _cache_arquivos
    
    if _pasta_temporaria_global and os.path.exists(_pasta_temporaria_global):
        try:
            shutil.rmtree(_pasta_temporaria_global)
            print(f"🗑️ Pasta temporária removida: {_pasta_temporaria_global}")

            _pasta_temporaria_global = None
            _cache_arquivos.clear()

            print("🧹 Cache de arquivos limpo")
            
            return {"status": "sucesso", "mensagem": "Pasta temporária e cache removidos com sucesso"}
        except Exception as e:
            return {"status": "erro", "mensagem": f"Erro ao remover pasta: {e}"}
    else:
        return {"status": "info", "mensagem": "Nenhuma pasta temporária para remover"}

def listar_cache_arquivos() -> Dict:
    """
    Lista arquivos atualmente no cache
    """
    global _cache_arquivos
    
    arquivos_cache = []
    total_mb = 0
    
    for chave, info in _cache_arquivos.items():
        if os.path.exists(info["arquivo_local"]):
            arquivos_cache.append({
                "nome": info["nome"],
                "linhas": info["linhas"],
                "colunas": info["colunas"],
                "tamanho_mb": info["tamanho_mb"],
                "arquivo_local": info["arquivo_local"]
            })
            total_mb += info["tamanho_mb"]
    
    return {
        "total_arquivos_cache": len(arquivos_cache),
        "total_tamanho_mb": round(total_mb, 2),
        "arquivos": arquivos_cache
    }

@tool("consultar_e_processar_arquivo")
def consultar_e_processar_arquivo(params: dict) -> Any:
    """
    Baixa arquivos da base e processa os dados.
    OTIMIZADO: Não baixa o mesmo arquivo duas vezes - usa cache inteligente.
    Mantém pasta temporária até comando /sair.

    Parâmetros esperados em *params*:
    - package_id (str): ID do pacote no Dados Abertos RJ
    - file_filter (str): filtro por nome do arquivo
    - operation (str): contar_linhas | media | soma | max | min | mostrar_colunas | preview | contar_por_valor
    - column (str): nome da coluna (obrigatório para contar_por_valor)
    - value (any): valor a ser contado (obrigatório para contar_por_valor)
    """
    
    try:
        package_id = params.get("package_id")
        file_filter = params.get("file_filter", "")
        operation = params.get("operation", "contar_linhas")

        if not package_id:
            return {"erro": "Parâmetro 'package_id' é obrigatório."}

        print(f"🔍 Buscando arquivos na base '{package_id}' com filtro '{file_filter}'")

        url = f"https://dadosabertos.rj.gov.br/api/3/action/package_show?id={package_id}"
        resp = requests.get(url, timeout=30)
        
        if resp.status_code != 200:
            return {"erro": f"Falha na requisição da API: HTTP {resp.status_code}"}
            
        data = resp.json()

        if not data.get("success") or "result" not in data:
            return {"erro": "Pacote não encontrado ou inacessível."}

        resources = data["result"].get("resources", [])
        if not resources:
            return {"erro": "Nenhum recurso encontrado no pacote."}

        if file_filter:
            matched = [r for r in resources if file_filter.lower() in r.get("name", "").lower()]
        else:
            matched = resources
            
        matched = matched[:5] 

        if not matched:
            return {"erro": f"Nenhum arquivo encontrado com o filtro: '{file_filter}'"}

        print(f"📁 Encontrados {len(matched)} arquivos para processar")

        pasta_temp = _criar_pasta_temporaria()
        resultados = {}
        arquivos_processados = 0
        downloads_realizados = 0
        cache_utilizados = 0

        for resource in matched:
            resultado_arquivo = _baixar_e_processar_arquivo(resource, pasta_temp)
            
            if not resultado_arquivo.get("sucesso"):
                nome = resource.get("name", "arquivo_sem_nome")
                resultados[nome] = resultado_arquivo
                continue
            
            df = resultado_arquivo["df"]
            nome = resultado_arquivo["nome"]
            
            if resultado_arquivo.get("do_cache"):
                cache_utilizados += 1
            else:
                downloads_realizados += 1
            
            if operation == "contar_linhas":
                memoria_mb = df.memory_usage(deep=True).sum() / (1024*1024)
                resultados[nome] = {
                    "linhas": len(df),
                    "colunas": len(df.columns),
                    "nomes_colunas": list(df.columns),
                    "memoria_mb": round(memoria_mb, 2),
                    "arquivo_local": resultado_arquivo["arquivo_local"],
                    "sucesso": True
                }
            elif operation == "mostrar_colunas":
                resultados[nome] = {
                    "colunas": list(df.columns),
                    "total_colunas": len(df.columns),
                    "linhas": len(df),
                    "tipos": df.dtypes.astype(str).to_dict(),
                    "arquivo_local": resultado_arquivo["arquivo_local"],
                    "sucesso": True
                }
            elif operation == "preview":
                resultados[nome] = {
                    "primeiras_5_linhas": df.head().to_dict('records'),
                    "colunas": list(df.columns),
                    "total_linhas": len(df),
                    "total_colunas": len(df.columns),
                    "arquivo_local": resultado_arquivo["arquivo_local"],
                    "sucesso": True
                }
            elif operation == "contar_por_valor":
                coluna = params.get("column")
                valor = params.get("value")

                if not coluna or valor is None:
                    resultados[nome] = {
                        "erro": "Parâmetros 'column' e 'value' são obrigatórios para a operação contar_por_valor",
                        "sucesso": False
                    }
                elif coluna not in df.columns:
                    resultados[nome] = {
                        "erro": f"Coluna '{coluna}' não encontrada no arquivo",
                        "colunas_disponiveis": list(df.columns),
                        "sucesso": False
                    }
                else:
                    try:
                        valor_convertido = int(valor)
                    except (ValueError, TypeError):
                        try:
                            valor_convertido = float(valor)
                        except (ValueError, TypeError):
                            valor_convertido = str(valor)

                    total = df[df[coluna] == valor_convertido].shape[0]

                    resultados[nome] = {
                        "coluna": coluna,
                        "valor": valor_convertido,
                        "total_registros": int(total),
                        "arquivo_local": resultado_arquivo["arquivo_local"],
                        "sucesso": True
                    }
            elif operation in ["media", "soma", "max", "min"]:
                numericas = df.select_dtypes(include=['number'])
                if not numericas.empty:
                    if operation == "media":
                        resultados[nome] = {"resultado": numericas.mean().to_dict(), "sucesso": True}
                    elif operation == "soma":
                        resultados[nome] = {"resultado": numericas.sum().to_dict(), "sucesso": True}
                    elif operation == "max":
                        resultados[nome] = {"resultado": numericas.max().to_dict(), "sucesso": True}
                    elif operation == "min":
                        resultados[nome] = {"resultado": numericas.min().to_dict(), "sucesso": True}
                    
                    resultados[nome]["arquivo_local"] = resultado_arquivo["arquivo_local"]
                else:
                    resultados[nome] = {"erro": "Nenhuma coluna numérica encontrada", "sucesso": False}
            else:
                resultados[nome] = {"erro": f"Operação desconhecida: {operation}", "sucesso": False}
                
            arquivos_processados += 1
            print(f"✅ Operação '{operation}' concluída com sucesso!")

        resultados["_resumo_processamento"] = {
            "pasta_temporaria": pasta_temp,
            "arquivos_solicitados": len(matched),
            "arquivos_processados_com_sucesso": arquivos_processados,
            "downloads_realizados": downloads_realizados,
            "cache_utilizados": cache_utilizados,
            "operacao_executada": operation,
            "observacao": "Pasta e cache mantidos até '/sair'",
            "cache_info": listar_cache_arquivos(),
            "sucesso_geral": arquivos_processados > 0
        }

        if arquivos_processados == 0:
            resultados["_resumo_processamento"]["mensagem_erro"] = "Nenhum arquivo foi processado com sucesso"

        return resultados

    except Exception as e:
        return {
            "erro": f"Falha geral no processamento: {str(e)}",
            "detalhes_tecnicas": "Erro na função principal da tool",
            "sucesso": False
        }