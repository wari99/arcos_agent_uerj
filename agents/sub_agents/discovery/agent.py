from pathlib import Path

from langchain.agents import create_agent

from agents.model import model
from agents.prompts import ROOT_PROMPT
from agents.prompts.commons.utils import load_prompt_from_markdown
from agents.sub_agents.delegation import delegar
from agents.sub_agents.discovery.tools.listar_bases import listar_bases
from agents.sub_agents.discovery.tools.buscar_infos_base import buscar_infos_base
from agents.sub_agents.discovery.tools.listar_recursos_da_base import listar_recursos_da_base
from agents.tools.commons.core import get_logger
from agents.tools.get_current_date import get_current_date

logger = get_logger("discovery")

ROLE_PROMPT = load_prompt_from_markdown(str(Path(__file__).parent / "prompts"))

# Sem checkpointer: cada chamada começa do zero e só o texto final volta ao supervisor
subagente_descoberta = create_agent(
    model=model,
    system_prompt=f"{ROOT_PROMPT}\n\n{ROLE_PROMPT}",
    tools=[
        listar_bases,
        buscar_infos_base,
        listar_recursos_da_base,
        get_current_date,
    ],
)


def executar(pedido: str) -> str:
    return delegar(subagente_descoberta, pedido, logger)
