import requests
from typing import Any
from langchain.tools import tool
import os
from dotenv import load_dotev

load_dotenv()

@tool("listar_bases")
def listar_bases(_: str = "") -> Any:
    """
    Retorna a lista de todas as bases disponíveis no Dados Abertos do RJ.
    
    """
    url = os.getenv("URL_LISTAR_BASES")
    try:
        resp = requests.get(url).json()
        return resp.get("result", [])
    except Exception as e:
        return {"erro": str(e)}