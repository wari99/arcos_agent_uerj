from langchain_core.tools import tool

from agents.sub_agents.documents.leitura import pdf, xlsx
from agents.sub_agents.documents.leitura.fonte import ErroDocumento, obter_fonte
from agents.sub_agents.documents.tools.mapear_documento import cabecalho_fonte
from agents.tools.commons.core import get_logger

logger = get_logger("documents")

MAX_LINHAS_PLANILHA = 60
MAX_LINHAS_CSV = 15
LIMITE_TEXTO_PAGINA_DE_FIGURA = (
    600  # página com imagem e muito texto costuma ser só logotipo ou foto
)


def _ler_pdf(f, paginas: str | None, max_caracteres: int) -> str:
    total = pdf.total_paginas(f.caminho)
    numeros = pdf.interpretar_intervalo(paginas, total)
    extraidas = pdf.extrair_paginas(f.caminho, numeros)

    blocos, usados, lidas = [], 0, []
    for p in extraidas:
        partes = [f"=== Página {p.numero} de {total} ==="]
        if p.sem_texto and not p.tabelas:
            partes.append(
                f"[sem texto: página provavelmente escaneada ou só imagem. Use interpretar_pagina({p.numero})]"
            )
        if p.texto:
            partes.append("[texto]\n" + p.texto)
        for i, t in enumerate(p.tabelas, 1):
            partes.append(f"[tabela extraída {i}]\n{t}")
        if p.tabelas_rejeitadas:
            partes.append(
                f"[a página tem tabela que não foi estruturada: o texto acima pode estar com colunas misturadas. "
                f"Se a tabela for importante, use interpretar_pagina({p.numero})]"
            )
        if p.possivel_grafico or (
            p.n_imagens and p.n_chars < LIMITE_TEXTO_PAGINA_DE_FIGURA
        ):
            partes.append(
                f"[a página tem imagem ou possível gráfico: se for relevante, use interpretar_pagina({p.numero})]"
            )
        bloco = "\n".join(partes)

        if usados + len(bloco) > max_caracteres and lidas:
            break
        if len(bloco) > max_caracteres:
            bloco = bloco[:max_caracteres] + "\n[página cortada por tamanho]"
        blocos.append(bloco)
        usados += len(bloco)
        lidas.append(p.numero)

    restante = [n for n in numeros if n not in lidas]
    rodape = (
        f"PÁGINAS LIDAS: {lidas[0]}-{lidas[-1]} de {total}"
        if lidas
        else "NENHUMA PÁGINA LIDA"
    )
    if restante:
        rodape += f" | NÃO CABERAM: {restante[0]}-{restante[-1]} (peça com paginas='{restante[0]}-{restante[-1]}')"
    elif lidas and lidas[-1] < total and not paginas:
        rodape += f" | O documento continua (páginas {lidas[-1] + 1}-{total})"
    return "\n".join(blocos + [rodape])


def _ler_xlsx(f, aba: str | None, max_caracteres: int) -> str:
    r = xlsx.ler_aba(f.caminho, f.tamanho_mb, aba, MAX_LINHAS_PLANILHA)
    saida = [f"ABAS DA PLANILHA: {', '.join(r['abas'])}"]
    if r["vazia"]:
        saida.append(f"A aba '{r['aba']}' está vazia.")
        return "\n".join(saida)

    saida.append(
        f"=== Aba '{r['aba']}' (cabeçalho na linha {r['linha_cabecalho']}) ==="
    )
    if r["introducao"]:
        saida.append("[título e notas antes da tabela]\n" + "\n".join(r["introducao"]))
    saida.append("[tabela extraída]\n" + xlsx.tabela_markdown(r["tabela"]))
    resumo = f"LINHAS: mostrando {r['linhas_mostradas']} de {r['linhas_total']}"
    if r["colunas_total"] > r["colunas_mostradas"]:
        resumo += (
            f" | COLUNAS: mostrando {r['colunas_mostradas']} de {r['colunas_total']}"
        )
    if r["linhas_total"] > r["linhas_mostradas"]:
        resumo += " | É só uma amostra: contas exatas sobre a tabela inteira devem ser feitas pela análise de dados."
    saida.append(resumo)
    texto = "\n".join(saida)
    return texto[:max_caracteres] + (
        "\n[cortado por tamanho]" if len(texto) > max_caracteres else ""
    )


def _ler_csv(f) -> str:
    from agents.tools.commons.utils import _processar_csv

    with open(f.caminho, "rb") as arquivo:
        df = _processar_csv(arquivo.read())
    if df is None or df.empty:
        return "Não consegui ler o CSV como tabela."
    amostra = [list(map(str, df.columns))] + [
        [xlsx._fmt(v) for v in linha]
        for linha in df.head(MAX_LINHAS_CSV).values.tolist()
    ]
    return (
        f"=== CSV: {len(df)} linhas x {len(df.columns)} colunas ===\n[tabela extraída]\n"
        f"{xlsx.tabela_markdown(amostra)}\n"
        "É só uma amostra: contas exatas devem ser feitas pela análise de dados."
    )


@tool("ler_documento")
def ler_documento(
    package_id: str,
    arquivo: str,
    paginas: str | None = None,
    aba: str | None = None,
    max_caracteres: int = 12000,
) -> str:
    """Lê o conteúdo de um documento já com o texto limpo (sem linhas em branco, cabeçalhos e rodapés repetidos),
    tabelas em Markdown e avisos de onde há gráficos ou páginas escaneadas.
    PDF: use 'paginas' como '1-3' ou '2,5-6' (sem informar, lê as primeiras 5 páginas).
    Planilha XLSX: use 'aba' com o nome da aba (sem informar, lê a primeira aba com conteúdo).
    'max_caracteres' limita o tamanho da resposta; se não couber tudo, o rodapé diz quais páginas faltam."""
    logger.info(
        f"ler_documento | {package_id} | {arquivo} | paginas={paginas} aba={aba}"
    )
    try:
        f = obter_fonte(package_id, arquivo)
        max_caracteres = max(2000, min(int(max_caracteres), 30000))
        if f.tipo == "pdf":
            corpo = _ler_pdf(f, paginas, max_caracteres)
        elif f.tipo == "xlsx":
            corpo = _ler_xlsx(f, aba, max_caracteres)
        elif f.tipo == "csv":
            corpo = _ler_csv(f)
        else:
            corpo = f"Tipo '{f.tipo}' não suportado para leitura (suportados: pdf, xlsx e csv)."
        return f"{cabecalho_fonte(f)}\n{corpo}"
    except ErroDocumento as e:
        return f"ERRO: {e}"
    except Exception as e:
        logger.exception("ler_documento falhou")
        return f"ERRO inesperado ao ler o documento: {e}"
