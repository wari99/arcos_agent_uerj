from pathlib import Path

from langchain.agents import create_agent
from langchain_core.tools import tool

from agents.model import model
from agents.prompts.commons.utils import load_prompt_from_markdown
from agents.sub_agents.delegation import delegar
from agents.sub_agents.documents.tools.buscar_no_documento import buscar_no_documento
from agents.sub_agents.documents.tools.interpretar_pagina import interpretar_pagina
from agents.sub_agents.documents.tools.ler_documento import ler_documento
from agents.sub_agents.documents.tools.listar_arquivos_da_base import (
    listar_arquivos_da_base,
)
from agents.sub_agents.documents.tools.mapear_documento import mapear_documento
from agents.tools.commons.core import get_logger

logger = get_logger("documents")

# Prompt próprio: não herda o ROOT_PROMPT (regras de SETRAM, pandas e filtros de arquivo, irrelevantes aqui)
PROMPT = load_prompt_from_markdown(str(Path(__file__).parent / "prompts"))

# Sem checkpointer: cada chamada começa do zero e só o texto final volta ao supervisor
subagente_documentos = create_agent(
    model=model,
    system_prompt=PROMPT,
    tools=[
        listar_arquivos_da_base,
        mapear_documento,
        ler_documento,
        buscar_no_documento,
        interpretar_pagina,
    ],
)


@tool("consultar_documentos")
def consultar_documentos(pedido: str) -> str:
    """Lê documentos (PDF e planilhas) de bases que NÃO são as principais de transporte (SETRAM e concessionárias)
    e extrai informação deles: responde perguntas sobre o conteúdo, resume, ou monta uma ficha com as principais
    informações. Entende tabelas, páginas escaneadas e gráficos, mas não faz contas exatas sobre tabelas grandes
    (para isso use analisar_arquivos). O pedido deve ser autocontido e SEMPRE trazer o package_id EXATO (o subagente
    não consegue achar a base pelo nome e não deve adivinhar ids): package_id, o modo (pergunta, resumo ou ficha),
    a pergunta e, se souber, o nome do arquivo (sem ele, o subagente lista os arquivos da base). Se você não tem o
    package_id exato, use descobrir_arquivos antes. Um pedido por base."""
    return delegar(subagente_documentos, pedido, logger)
