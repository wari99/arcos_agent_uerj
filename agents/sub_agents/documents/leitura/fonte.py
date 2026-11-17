"""Obtém um arquivo de uma base: resolve o recurso pelo nome, baixa para a pasta da sessão e detecta o tipo."""
import glob
import hashlib
import os
import tempfile
import time
import unicodedata
import zipfile
from dataclasses import dataclass, field

import requests

from agents.tools.commons.core import get_logger
from agents.tools.commons.settings import TIMEOUT_DOWNLOAD_SEGUNDOS, TIMEOUT_REQUISICAO
from agents.tools.commons.utils import _estado

logger = get_logger("documents")

LIMITE_DOWNLOAD_MB = 80
TTL_BASE_SEGUNDOS = 600
MAX_NOMES_NA_MENSAGEM = 15

_CACHE_BASES: dict[str, tuple[float, dict]] = {}

# O agente tende a "chutar" outros ids quando a base não existe (cada chute é uma ida à API): a mensagem o impede
_BASE_INEXISTENTE = (
    "A base '{package_id}' NÃO existe no catálogo. NÃO tente adivinhar outros package_id. "
    "Encerre e responda ao supervisor que falta o package_id exato (ele deve obtê-lo com descobrir_arquivos)."
)


class ErroDocumento(Exception):
    """Erro esperado (mensagem já pronta para o agente)."""


@dataclass
class Fonte:
    package_id: str
    nome: str
    url: str
    caminho: str
    tipo: str  # pdf | xlsx | csv | docx | pptx | xls | zip | html | desconhecido
    tamanho_mb: float
    base: dict = field(default_factory=dict)  # título, órgão, descrição, atualização


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, só letras e números separados por espaço."""
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", texto or "")
        if not unicodedata.combining(c)
    )
    return " ".join(
        "".join(c if c.isalnum() else " " for c in sem_acento.lower()).split()
    )


def _consultar_base(package_id: str) -> dict:
    cache = _CACHE_BASES.get(package_id)
    if cache and time.time() - cache[0] < TTL_BASE_SEGUNDOS:
        return cache[1]

    modelo_url = os.getenv("URL_CONSULTAR_PROCESSAR_ARQUIVO")
    if not modelo_url:
        raise ErroDocumento(
            "Variável de ambiente URL_CONSULTAR_PROCESSAR_ARQUIVO não configurada."
        )
    try:
        resp = requests.get(modelo_url.format(package_id), timeout=TIMEOUT_REQUISICAO)
        resp.raise_for_status()
        dados = resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise ErroDocumento(_BASE_INEXISTENTE.format(package_id=package_id))
        raise ErroDocumento(f"Erro ao consultar a base '{package_id}': {e}")
    except requests.exceptions.RequestException as e:
        raise ErroDocumento(f"Erro ao consultar a base '{package_id}': {e}")
    except ValueError:
        raise ErroDocumento(f"Resposta inválida da API para a base '{package_id}'.")

    if not dados.get("success"):
        raise ErroDocumento(_BASE_INEXISTENTE.format(package_id=package_id))

    resultado = dados["result"]
    _CACHE_BASES[package_id] = (time.time(), resultado)
    return resultado


def _nome_na_url(recurso: dict) -> str:
    return os.path.basename((recurso.get("url") or "").split("?")[0])


def _lista_nomes(recursos: list[dict]) -> str:
    nomes = [f"'{r.get('name') or _nome_na_url(r)}'" for r in recursos]
    texto = "; ".join(nomes[:MAX_NOMES_NA_MENSAGEM])
    if len(nomes) > MAX_NOMES_NA_MENSAGEM:
        texto += f" (+{len(nomes) - MAX_NOMES_NA_MENSAGEM})"
    return texto


def _escolher_recurso(recursos: list[dict], arquivo: str) -> dict:
    if not recursos:
        raise ErroDocumento("A base não tem arquivos.")

    alvo = normalizar(arquivo)
    if not alvo:
        if len(recursos) == 1:
            return recursos[0]
        raise ErroDocumento(f"Informe o arquivo. Disponíveis: {_lista_nomes(recursos)}")

    def nomes(r):
        return normalizar(r.get("name", "")), normalizar(_nome_na_url(r))

    for (
        r
    ) in (
        recursos
    ):  # nome idêntico, respeitando maiúsculas (a base pode ter nomes que só diferem nisso)
        if arquivo.strip() in (r.get("name", ""), _nome_na_url(r)):
            return r

    iguais = [r for r in recursos if alvo in nomes(r)]
    if len(iguais) == 1:
        return iguais[0]
    if len(iguais) > 1:
        raise ErroDocumento(
            f"'{arquivo}' é ambíguo (nomes quase idênticos). Use o nome exato, com maiúsculas: {_lista_nomes(iguais)}"
        )

    candidatos = [r for r in recursos if any(alvo in n for n in nomes(r))]
    if not candidatos:  # todas as palavras presentes, em qualquer ordem
        palavras = alvo.split()
        candidatos = [
            r for r in recursos if any(all(p in n for p in palavras) for n in nomes(r))
        ]

    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        raise ErroDocumento(
            f"Nenhum arquivo casa com '{arquivo}'. Disponíveis: {_lista_nomes(recursos)}"
        )
    raise ErroDocumento(
        f"'{arquivo}' é ambíguo. Candidatos: {_lista_nomes(candidatos)}"
    )


def _pasta_documentos() -> str:
    """Subpasta da pasta temporária da sessão (apagada no /sair pela limpeza existente)."""
    if _estado.pasta_temporaria_global is None or not os.path.exists(
        _estado.pasta_temporaria_global
    ):
        _estado.pasta_temporaria_global = tempfile.mkdtemp(prefix="arcos_rj_")
    pasta = os.path.join(_estado.pasta_temporaria_global, "documentos")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _tipo_pelo_conteudo(caminho: str, nome: str, mimetype: str) -> str:
    """O campo 'format' do catálogo tem muitos erros de digitação; o conteúdo é mais confiável."""
    with open(caminho, "rb") as f:
        inicio = f.read(8)

    if inicio.startswith(b"%PDF"):
        return "pdf"
    if inicio.startswith(b"PK"):
        try:
            with zipfile.ZipFile(caminho) as z:
                nomes = z.namelist()
        except zipfile.BadZipFile:
            return "desconhecido"
        if any(n.startswith("xl/") for n in nomes):
            return "xlsx"
        if any(n.startswith("word/") for n in nomes):
            return "docx"
        if any(n.startswith("ppt/") for n in nomes):
            return "pptx"
        return "zip"
    if inicio.startswith(b"\xd0\xcf\x11\xe0"):  # formato binário antigo do Office
        referencia = f"{nome} {mimetype}".lower()
        return "xls" if ("xls" in referencia or "excel" in referencia) else "doc_legado"
    if inicio.lstrip().lower().startswith((b"<!doc", b"<html")):
        return "html"
    if nome.lower().endswith((".csv", ".txt")) or "csv" in (mimetype or "").lower():
        return "csv"
    return "desconhecido"


def _baixar(url: str, destino: str) -> None:
    temporario = destino + ".parcial"
    limite = LIMITE_DOWNLOAD_MB * 1024 * 1024
    try:
        with requests.get(
            url, stream=True, timeout=(10, TIMEOUT_DOWNLOAD_SEGUNDOS)
        ) as resp:
            resp.raise_for_status()
            total = 0
            with open(temporario, "wb") as f:
                for pedaco in resp.iter_content(chunk_size=256 * 1024):
                    total += len(pedaco)
                    if total > limite:
                        raise ErroDocumento(
                            f"Arquivo maior que o limite de {LIMITE_DOWNLOAD_MB} MB."
                        )
                    f.write(pedaco)
        os.replace(temporario, destino)
    except requests.exceptions.RequestException as e:
        raise ErroDocumento(f"Erro ao baixar o arquivo: {e}")
    finally:
        if os.path.exists(temporario):
            os.remove(temporario)


def obter_fonte(package_id: str, arquivo: str) -> Fonte:
    package_id = (package_id or "").strip()
    if not package_id:
        raise ErroDocumento("Parâmetro 'package_id' obrigatório.")

    base = _consultar_base(package_id)
    recurso = _escolher_recurso(base.get("resources", []), arquivo)
    url = recurso.get("url")
    if not url:
        raise ErroDocumento("O recurso não tem URL de download.")

    nome = recurso.get("name") or _nome_na_url(recurso) or "arquivo"
    base_cache = os.path.join(
        _pasta_documentos(), hashlib.sha1(url.encode()).hexdigest()[:16]
    )
    caminho = next((c for c in glob.glob(base_cache + ".*")), None)

    if caminho:
        logger.info(f"arquivo já em cache: {nome}")
        tipo = os.path.splitext(caminho)[1].lstrip(".")
    else:
        logger.info(f"baixando: {nome}")
        _baixar(url, base_cache)
        tipo = _tipo_pelo_conteudo(base_cache, nome, recurso.get("mimetype", ""))
        # a extensão segue o CONTEÚDO (o catálogo troca tipos) e é exigida por algumas bibliotecas (openpyxl)
        caminho = f"{base_cache}.{tipo}"
        os.replace(base_cache, caminho)
    organizacao = base.get("organization") or {}
    return Fonte(
        package_id=package_id,
        nome=nome,
        url=url,
        caminho=caminho,
        tipo=tipo,
        tamanho_mb=round(os.path.getsize(caminho) / (1024 * 1024), 2),
        base={
            "titulo": base.get("title", ""),
            "orgao": organizacao.get("title", "")
            if isinstance(organizacao, dict)
            else "",
            "descricao": (base.get("notes") or "").strip(),
            "atualizado_em": (base.get("metadata_modified") or "")[:10],
        },
    )
