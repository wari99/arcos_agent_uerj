from langchain_core.tools import tool

from agents.sub_agents.documents.leitura import pdf, xlsx
from agents.sub_agents.documents.leitura.fonte import ErroDocumento, Fonte, obter_fonte
from agents.tools.commons.core import get_logger

logger = get_logger("documents")


def cabecalho_fonte(f: Fonte) -> str:
    linhas = [
        f"ARQUIVO: {f.nome}",
        f"BASE: {f.package_id} | {f.base.get('titulo', '')} | órgão: {f.base.get('orgao') or 'n/d'} "
        f"| atualizada em: {f.base.get('atualizado_em') or 'n/d'}",
        f"TIPO: {f.tipo} | TAMANHO: {f.tamanho_mb} MB",
    ]
    return "\n".join(linhas)


def _lista(paginas) -> str:
    return ", ".join(str(p) for p in paginas) if paginas else "nenhuma"


@tool("mapear_documento")
def mapear_documento(package_id: str, arquivo: str) -> str:
    """Dá uma visão rápida de um documento ANTES de lê-lo: tipo, tamanho, número de páginas ou abas,
    se é PDF escaneado, quais páginas têm tabelas, imagens ou possíveis gráficos, sumário e o início do texto.
    Use sempre primeiro. Parâmetros: package_id (id da base) e arquivo (nome do arquivo na base, ou parte dele)."""
    logger.info(f"mapear_documento | {package_id} | {arquivo}")
    try:
        f = obter_fonte(package_id, arquivo)
        saida = [cabecalho_fonte(f)]
        descricao = f.base.get("descricao", "")
        if descricao:
            saida.append(f"DESCRIÇÃO DA BASE: {descricao[:400]}")

        if f.tipo == "pdf":
            m = pdf.mapear(f.caminho)
            saida.append(
                f"PDF: {m['total_paginas']} páginas (analisadas {m['paginas_analisadas']}) | "
                f"escaneado: {'SIM (precisa de interpretar_pagina)' if m['escaneado'] else 'não'}"
            )
            saida.append(f"PÁGINAS SEM TEXTO: {_lista(m['sem_texto'])}")
            saida.append(f"PÁGINAS COM TABELA (verificadas até a {m['tabelas_analisadas_ate']}): {_lista(m['com_tabelas'])}")
            saida.append(f"PÁGINAS COM IMAGENS: {_lista(m['com_imagens'])}")
            saida.append(f"PÁGINAS COM POSSÍVEL GRÁFICO (heurística): {_lista(m['possivel_grafico'])}")
            if m["sumario"]:
                saida.append("SUMÁRIO DO PDF:\n" + "\n".join(m["sumario"]))
            if m["inicio"]:
                saida.append(f"INÍCIO DO DOCUMENTO:\n{m['inicio']}")
        elif f.tipo == "xlsx":
            abas = xlsx.mapear(f.caminho, f.tamanho_mb)
            saida.append(f"PLANILHA: {len(abas)} aba(s)")
            for a in abas:
                extras = []
                if a["mesclagens"]:
                    extras.append(f"{a['mesclagens']} mesclagens")
                if a["graficos"]:
                    extras.append(f"{a['graficos']} gráfico(s)")
                if a["imagens"]:
                    extras.append(f"{a['imagens']} imagem(ns)")
                if not a["visivel"]:
                    extras.append("oculta")
                saida.append(f"- aba '{a['aba']}': {a['dimensoes']}" + (f" ({', '.join(extras)})" if extras else ""))
        elif f.tipo == "csv":
            saida.append("CSV: tabela de dados. Para contas e filtros, o caminho é a análise de dados (analisar_arquivos).")
        else:
            saida.append(f"Tipo '{f.tipo}' não suportado para leitura (suportados: pdf, xlsx e csv).")

        return "\n".join(saida)
    except ErroDocumento as e:
        return f"ERRO: {e}"
    except Exception as e:
        logger.error(f"mapear_documento falhou: {e}", exc_info=True)
        return f"ERRO inesperado ao mapear o documento: {e}"
