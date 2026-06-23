import requests
from typing import Any
from langchain.tools import tool

@tool("listar_bases")
def listar_bases(_: str = "") -> Any:
    """
    Retorna a lista de todas as bases disponíveis no Dados Abertos do RJ.
    
    """
    url = "https://dadosabertos.rj.gov.br/api/3/action/package_list"
    try:
        resp = requests.get(url).json()
        return resp.get("result", [])
    except Exception as e:
        return {"erro": str(e)}