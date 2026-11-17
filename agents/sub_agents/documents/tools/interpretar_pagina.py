import time

from langchain_core.tools import tool

from agents.sub_agents.documents.leitura import pdf, visao
from agents.sub_agents.documents.leitura.fonte import ErroDocumento, obter_fonte
from agents.tools.commons.core import get_logger

logger = get_logger("documents")


@tool("interpretar_pagina")
def interpretar_pagina(
    package_id: str, arquivo: str, pagina: int, pergunta: str | None = None
) -> str:
    """Lê UMA página de um PDF como imagem (visão do Gemini). Use quando a página for escaneada (sem texto),
    tiver gráfico ou figura, ou tiver uma tabela que a leitura normal não conseguiu extrair direito.
    Mais lenta e mais cara que ler_documento: use só nas páginas necessárias.
    Valores lidos de gráficos são aproximados, a menos que estejam escritos no próprio gráfico.
    'pergunta' (opcional) diz o que procurar na página."""
    logger.info(f"interpretar_pagina | {package_id} | {arquivo} | página {pagina}")
    try:
        f = obter_fonte(package_id, arquivo)
        if f.tipo != "pdf":
            return f"ERRO: interpretar_pagina só funciona com PDF (este arquivo é '{f.tipo}')."
        png = pdf.renderizar_png(f.caminho, int(pagina))
        inicio = time.perf_counter()
        descricao = visao.descrever_pagina(png, int(pagina), pergunta or "")
        logger.info(
            f"interpretar_pagina | visão concluída em {time.perf_counter() - inicio:.1f}s"
        )
        if not descricao:
            return f"ERRO: o modelo não devolveu texto para a página {pagina}."
        return (
            f"ARQUIVO: {f.nome} | página {pagina}\n"
            "[interpretado por visão: transcrição automática. Pode conter erros e valores de gráfico são aproximados]\n"
            f"{descricao}"
        )
    except ErroDocumento as e:
        return f"ERRO: {e}"
    except Exception as e:
        logger.exception("interpretar_pagina falhou")
        return f"ERRO inesperado ao interpretar a página: {e}"
