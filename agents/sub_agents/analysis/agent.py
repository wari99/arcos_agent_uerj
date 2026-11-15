from pathlib import Path

from langchain.agents import create_agent

from agents.model import model
from agents.prompts import ROOT_PROMPT
from agents.prompts.commons.utils import load_prompt_from_markdown
from agents.sub_agents.analysis.tools.baixar_arquivo_dados import baixar_arquivo_dados_tool
from agents.sub_agents.analysis.tools.analisar_dados_arquivo import analisar_dados_arquivo
from agents.sub_agents.analysis.tools.gerenciar_cache_sessao import gerenciar_cache_sessao
from agents.sub_agents.analysis.tools.gerar_graficos import gerar_graficos
from agents.sub_agents.delegation import delegar
from agents.tools.commons.core import get_logger

logger = get_logger("analysis")

ROLE_PROMPT = load_prompt_from_markdown(str(Path(__file__).parent / "prompts"))

# Sem checkpointer: cada chamada começa do zero e só o texto final volta ao supervisor
subagente_analise = create_agent(
    model=model,
    system_prompt=f"{ROOT_PROMPT}\n\n{ROLE_PROMPT}",
    tools=[
        baixar_arquivo_dados_tool,
        analisar_dados_arquivo,
        gerenciar_cache_sessao,
        gerar_graficos,
    ],
)


def executar(pedido: str) -> str:
    return delegar(subagente_analise, pedido, logger)
