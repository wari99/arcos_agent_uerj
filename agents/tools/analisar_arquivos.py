from langchain_core.tools import tool
from agents.sub_agents.analysis.agent import executar

@tool("analisar_arquivos")
def analisar_arquivos(pedido: str) -> str:
    """Baixa e analisa arquivos de dados e gera gráficos. Retorna números finais, fonte (base, arquivo, tipo)
    e filtros usados. O pedido deve ser autocontido (package_id, nomes exatos dos arquivos, filtros, métrica)."""
    return executar(pedido)
