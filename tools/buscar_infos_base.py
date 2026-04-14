import requests
from typing import Any, List
from langchain.tools import tool
import os
from dotenv import load_dotenv

load_dotenv()

@tool("buscar_infos_base")
def buscar_infos_base(base_nome: str, limite: int = 3) -> Any:
    """
    Busca bases pelo nome e retorna informações semânticas
    suficientes para decisão do LLM.

    Parâmetros:
    - base_nome: nome da base a buscar
    - limite: quantos datasets retornar (default=3)
    """

    buscar_bases_template = os.getenv("URL_BUSCAR_BASE")
    url = buscar_bases_template.format(base_nome)

    try:
        resp = requests.get(url).json()
        result = resp.get("result")

        if not result:
            return {
                "total_encontrado": 0,
                "bases": []
            }

        bases_resumidas: List[dict] = []

        for item in result.get("results", [])[:limite]:
            bases_resumidas.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "title": item.get("title"),
                "description": item.get("notes"),
                "num_resources": item.get("num_resources"),
                "organization": (
                    item.get("organization", {}).get("title")
                )
            })

        return {
            "total_encontrado": result.get("count", 0),
            "bases": bases_resumidas
        }

    except Exception as e:
        return {"erro": str(e)}