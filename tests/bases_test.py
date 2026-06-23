import requests
import os
from dotenv import load_dotenv
import json

"""
Nome: Teste de bases

Descrição: 
    Testar os retornos do endpoint da API que guarda os nomes das bases de dados disponíveis.
    Salva os resultados em um JSON chamado listar_bases para melhor visualização.

Objetivo: Reunir em um só arquivo todos os nomes das bases.
"""

load_dotenv()

url = os.getenv("URL_LISTAR_BASES")

print(f"URL: {url}\n")

resp = requests.get(url).json()

with open("listar_bases.json", "w", encoding="utf-8") as f:
    json.dump(resp, f, ensure_ascii=False, indent=4)