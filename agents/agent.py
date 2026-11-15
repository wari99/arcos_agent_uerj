# Agente ARCOS orquestrador: delega tarefas para os subagentes
from pathlib import Path

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from agents.model import model
from agents.prompts import ROOT_PROMPT
from agents.prompts.commons.utils import load_prompt_from_markdown
from agents.sub_agents.discovery.tools.buscar_infos_base import buscar_infos_base
from agents.sub_agents.documents.agent import consultar_documentos
from agents.tools.analisar_arquivos import analisar_arquivos
from agents.tools.descobrir_arquivos import descobrir_arquivos
from agents.tools.get_current_date import get_current_date

SUPERVISOR_PROMPT = load_prompt_from_markdown(str(Path(__file__).parent / "prompts" / "supervisor"))

agent_memory = create_agent(
    model=model,
    system_prompt=f"{ROOT_PROMPT}\n\n{SUPERVISOR_PROMPT}",
    tools=[buscar_infos_base, descobrir_arquivos, analisar_arquivos, consultar_documentos, get_current_date],
    checkpointer=InMemorySaver(),
)
