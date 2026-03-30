import os
import io
import zipfile
import tempfile
import requests
import pandas as pd
import shutil
from typing import Any
from langchain.tools import tool

@tool("limpeza_encerramento")
def limpeza_encerramento() -> str:
    """
    Limpa todos os diretórios temporários armazenados na memória do agente.
    Deve ser chamado quando o usuário encerra o fluxo (ex: '/sair').
    """
    tmp_dirs = agent_memory.get("tmp_dirs_ativos") or []
    sucesso = []
    falha = []

    for tmp_dir in tmp_dirs:
        if os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
                sucesso.append(tmp_dir)
            except Exception:
                falha.append(tmp_dir)

    agent_memory.set("tmp_dirs_ativos", [])

    return f"🗑️ Limpeza concluída. Sucesso: {len(sucesso)}, Falha: {len(falha)}"
