from langchain_core.tools import tool
from agents.sub_agents.discovery.agent import executar

@tool("descobrir_arquivos")
def descobrir_arquivos(pedido: str) -> str:
    """Descobre bases e arquivos disponíveis. Use para listar bases, obter informações de uma base,
    listar/contar arquivos e verificar quais períodos existem ou faltam. Percorre todas as páginas.
    O pedido deve ser autocontido (base, termo de busca, período desejado)."""
    return executar(pedido)
