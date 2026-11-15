from langchain_core.tools import tool

from agents.sub_agents.documents.leitura.fonte import ErroDocumento, _consultar_base, _nome_na_url
from agents.tools.commons.core import get_logger

logger = get_logger("documents")

MAX_ARQUIVOS = 80


@tool("listar_arquivos_da_base")
def listar_arquivos_da_base(package_id: str) -> str:
    """Lista os arquivos de uma base pelo package_id EXATO (nome, formato informado pelo catálogo e tamanho).
    Use quando o pedido não trouxe o nome do arquivo. Se a base não existir, NÃO tente outros ids."""
    logger.info(f"listar_arquivos_da_base | {package_id}")
    try:
        base = _consultar_base(package_id)
    except ErroDocumento as e:
        return f"ERRO: {e}"
    except Exception as e:
        logger.error(f"listar_arquivos_da_base falhou: {e}", exc_info=True)
        return f"ERRO inesperado ao listar a base: {e}"

    recursos = base.get("resources", [])
    linhas = [f"BASE: {package_id} | {base.get('title', '')} | {len(recursos)} arquivo(s)"]
    for r in recursos[:MAX_ARQUIVOS]:
        tamanho = f"{r['size'] / 1024 ** 2:.1f} MB" if r.get("size") else "tamanho n/d"
        linhas.append(f"- {r.get('name') or _nome_na_url(r)} | {(r.get('format') or 'n/d').upper()} | {tamanho}")
    if len(recursos) > MAX_ARQUIVOS:
        linhas.append(f"(+{len(recursos) - MAX_ARQUIVOS} arquivos não listados)")
    return "\n".join(linhas)
