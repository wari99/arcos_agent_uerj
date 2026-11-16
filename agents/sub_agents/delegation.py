#evitar que um subagente fique em laço de tentativas
LIMITE_PASSOS = 40

import logging
import re
import time
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

def _ferramentas_chamadas(mensagens) -> list:
    """Nomes das ferramentas que o subagente chamou, na ordem (inclui repetições, ex.: paginação)."""
    return [
        tc["name"]
        for m in mensagens
        if getattr(m, "type", None) == "ai"
        for tc in (getattr(m, "tool_calls", None) or [])
    ]

_CAMINHO_PNG = re.compile(r"""[^\s'"]+\.png""")

def _graficos_gerados(mensagens) -> list:
    """Caminhos .png devolvidos pelas ferramentas (o texto final do subagente costuma omiti-los)."""
    caminhos = []
    for m in mensagens:
        if getattr(m, "type", None) == "tool":
            for c in _CAMINHO_PNG.findall(str(m.content)):
                if c.startswith("/") and c not in caminhos:  # só caminhos absolutos (ignora o nome solto do arquivo)
                    caminhos.append(c)
    return caminhos

def delegar(subagente, pedido: str, logger: logging.Logger) -> str:
    """Invoca o subagente e devolve só o texto final (nunca vazio)."""
    logger.info(f"delegado pelo supervisor | pedido: {pedido[:300]}")
    inicio = time.perf_counter()
    try:
        resultado = subagente.invoke(
            {"messages": [HumanMessage(content=pedido)]},
            config={"recursion_limit": LIMITE_PASSOS},
        )
        texto = resultado["messages"][-1].text.strip()
    except GraphRecursionError:
        logger.error(f"interrompido após {time.perf_counter() - inicio:.1f}s: limite de {LIMITE_PASSOS} passos")
        return (
            "Erro ao executar a consulta: o subagente excedeu o limite de passos sem concluir. "
            "Refaça o pedido com mais detalhes (package_id exato, nome do arquivo)."
        )
    except Exception as e:
        logger.error(f"falhou após {time.perf_counter() - inicio:.1f}s: {e}")
        return f"Erro ao executar a consulta: {e}"

    # a interface só exibe o gráfico se o caminho do .png estiver no texto final; o subagente enxuto o omite
    for caminho in _graficos_gerados(resultado["messages"]):
        if caminho not in texto:
            texto += f"\n\nGráfico gerado: {caminho}"

    chamadas = _ferramentas_chamadas(resultado["messages"])
    logger.info(
        f"concluído em {time.perf_counter() - inicio:.1f}s | "
        f"{len(chamadas)} chamada(s) de ferramenta: {chamadas} | resposta: {len(texto)} caracteres"
    )
    if not texto:
        logger.warning("resposta vazia; retornando 'Nenhum resultado.'")
    return texto or "Nenhum resultado."
