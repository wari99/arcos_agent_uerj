from langchain_core.tools import tool

from agents.sub_agents.documents.leitura import pdf, xlsx
from agents.sub_agents.documents.leitura.fonte import ErroDocumento, obter_fonte
from agents.tools.commons.core import get_logger

logger = get_logger("documents")

TRECHO = 110


def _dobrar(texto: str) -> str:
    """Minúsculas e sem acento, mantendo o MESMO tamanho (um caractere vira um caractere) para alinhar trechos."""
    import unicodedata

    return "".join(unicodedata.normalize("NFD", c)[0].lower()[:1] for c in texto)


def _trechos(texto: str, alvo: str, maximo: int):
    dobrado = _dobrar(texto)
    posicoes, inicio = [], 0
    while len(posicoes) < maximo:
        i = dobrado.find(alvo, inicio)
        if i < 0:
            break
        posicoes.append(i)
        inicio = i + len(alvo)
    return [
        " ".join(texto[max(0, i - TRECHO) : i + len(alvo) + TRECHO].split())
        for i in posicoes
    ]


@tool("buscar_no_documento")
def buscar_no_documento(
    package_id: str, arquivo: str, termo: str, max_resultados: int = 8
) -> str:
    """Procura uma palavra ou expressão DENTRO de um documento (sem diferenciar maiúsculas nem acentos) e diz em
    quais páginas (PDF) ou células (planilha) ela aparece, com um trecho de cada. Útil para ler só as páginas
    relevantes de um documento grande."""
    logger.info(f"buscar_no_documento | {package_id} | {arquivo} | termo={termo}")
    try:
        termo = (termo or "").strip()
        if not termo:
            return "ERRO: informe o termo a buscar."
        maximo = max(1, min(int(max_resultados), 20))
        f = obter_fonte(package_id, arquivo)
        alvo = _dobrar(termo)

        if f.tipo == "pdf":
            achados = []
            for numero, texto in enumerate(pdf.texto_para_busca(f.caminho), 1):
                trechos = _trechos(texto, alvo, 2)
                if trechos:
                    contagem = _dobrar(texto).count(alvo)
                    achados.append((numero, contagem, trechos))
            if not achados:
                return f"'{termo}' não aparece no texto de {f.nome}. Se o PDF for escaneado, o texto pode não estar disponível (veja mapear_documento)."
            linhas = [f"'{termo}' em {f.nome}: {len(achados)} página(s)"]
            for numero, contagem, trechos in achados[:maximo]:
                linhas.append(
                    f"- página {numero} ({contagem}x): "
                    + " [...] ".join(f'"{t}"' for t in trechos)
                )
            if len(achados) > maximo:
                linhas.append(f"(+{len(achados) - maximo} páginas)")
            return "\n".join(linhas)

        if f.tipo == "xlsx":
            achados = xlsx.buscar(f.caminho, f.tamanho_mb, termo, maximo)
            if not achados:
                return f"'{termo}' não aparece na planilha {f.nome}."
            linhas = [f"'{termo}' em {f.nome}:"]
            linhas += [
                f"- aba '{a['aba']}', célula {a['celula']}: {a['linha']}"
                for a in achados
            ]
            return "\n".join(linhas)

        return f"Busca não disponível para o tipo '{f.tipo}' (suportados: pdf e xlsx)."
    except ErroDocumento as e:
        return f"ERRO: {e}"
    except Exception as e:
        logger.exception("buscar_no_documento falhou")
        return f"ERRO inesperado na busca: {e}"
