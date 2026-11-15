"""Progresso em tempo real para a interface web.

Um callback do LangChain recebe o início e o fim de cada ferramenta (do supervisor e dos subagentes, que herdam
o callback do pai) e as ferramentas em si não precisam mudar. A execução do agente roda numa thread secundária
e a thread principal (Streamlit) lê os eventos de uma fila para atualizar a tela.
"""
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler

ROTULOS = {
    "descobrir_arquivos": "Buscando bases e arquivos",
    "analisar_arquivos": "Analisando os dados",
    "consultar_documentos": "Lendo documentos",
    "get_current_date": "Consultando a data atual",
    "listar_bases": "Listando as bases do portal",
    "buscar_infos_base": "Buscando base pelo nome",
    "listar_recursos_da_base": "Listando arquivos da base",
    "baixar_arquivo_dados_tool": "Baixando arquivo",
    "gerenciar_cache_sessao": "Verificando arquivos em cache",
    "analisar_dados_arquivo": "Calculando",
    "gerar_graficos": "Gerando gráfico",
    "listar_arquivos_da_base": "Listando arquivos da base",
    "mapear_documento": "Mapeando o documento",
    "ler_documento": "Lendo o documento",
    "buscar_no_documento": "Procurando no documento",
    "interpretar_pagina": "Interpretando a página (visão)",
}

# Ferramentas do supervisor que acionam um subagente; as demais, enquanto uma delas roda, são do subagente
DELEGACOES = {"descobrir_arquivos", "analisar_arquivos", "consultar_documentos"}

# Argumentos que ajudam a identificar o que está sendo feito, em ordem de prioridade
_CHAVES_DETALHE = (
    "operation", "operacao", "acao", "arquivo", "package_id", "base_nome",
    "termo_busca", "termo", "tipo_grafico", "pagina", "paginas", "aba",
)


def _detalhe(nome: str, entrada: Any) -> str:
    if not isinstance(entrada, dict):
        return ""
    if nome in DELEGACOES:
        return str(entrada.get("pedido", ""))[:90]
    campos = dict(entrada)
    if isinstance(entrada.get("params"), dict):
        campos.update(entrada["params"])
    partes = [f"{c}={str(campos[c])[:40]}" for c in _CHAVES_DETALHE if campos.get(c) not in (None, "")]
    return ", ".join(partes[:3])


class ProgressoCallback(BaseCallbackHandler):
    """Publica eventos numa fila: ("inicio", id, nivel, texto), ("fim", id, ok) e ("llm", ativo)."""

    def __init__(self, fila: "queue.Queue"):
        self.fila = fila
        self._lock = threading.Lock()
        self._delegacao_do_run: Dict[Any, bool] = {}
        self._delegando = 0

    def on_tool_start(self, serialized, input_str, *, run_id, inputs=None, **kwargs):
        nome = kwargs.get("name") or (serialized or {}).get("name") or "ferramenta"
        eh_delegacao = nome in DELEGACOES
        with self._lock:
            nivel = 1 if (self._delegando > 0 and not eh_delegacao) else 0
            self._delegacao_do_run[run_id] = eh_delegacao
            if eh_delegacao:
                self._delegando += 1
        texto = ROTULOS.get(nome, nome)
        detalhe = _detalhe(nome, inputs)
        self.fila.put(("inicio", run_id, nivel, f"{texto} ({detalhe})" if detalhe else texto))

    def on_tool_end(self, output, *, run_id, **kwargs):
        self._encerrar(run_id, True)

    def on_tool_error(self, error, *, run_id, **kwargs):
        self._encerrar(run_id, False)

    def _encerrar(self, run_id, ok: bool):
        with self._lock:
            if self._delegacao_do_run.pop(run_id, False):
                self._delegando -= 1
        self.fila.put(("fim", run_id, ok))

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.fila.put(("llm", True))

    def on_llm_end(self, response, **kwargs):
        self.fila.put(("llm", False))


def executar_com_progresso(
    agente,
    entrada: dict,
    config: dict,
    atualizar: Callable[[List[dict], str, float], None],
    intervalo: float = 0.3,
):
    """Roda agente.invoke numa thread e chama atualizar(linhas, atividade, segundos) enquanto espera.

    linhas: [{"texto", "nivel", "estado" ("rodando"|"ok"|"erro"), "duracao"}]. Devolve o resultado do agente
    ou relança a exceção que ele tiver levantado.
    """
    fila: "queue.Queue" = queue.Queue()
    config = {**config, "callbacks": [ProgressoCallback(fila)]}
    saida: Dict[str, Any] = {}

    def _rodar():
        try:
            saida["resultado"] = agente.invoke(entrada, config=config)
        except BaseException as e:  # noqa: BLE001 - repassado à thread principal
            saida["erro"] = e
        finally:
            fila.put(("fim_geral",))

    threading.Thread(target=_rodar, daemon=True).start()

    inicio = time.perf_counter()
    linhas: List[dict] = []
    por_id: Dict[Any, dict] = {}
    llm_ativo = False
    terminou = False

    while not terminou:
        try:
            evento: Optional[tuple] = fila.get(timeout=intervalo)
        except queue.Empty:
            evento = None

        # esvazia a fila inteira antes de redesenhar
        while evento is not None:
            tipo = evento[0]
            if tipo == "inicio":
                _, run_id, nivel, texto = evento
                linha = {"texto": texto, "nivel": nivel, "estado": "rodando", "t0": time.perf_counter(), "duracao": None}
                linhas.append(linha)
                por_id[run_id] = linha
            elif tipo == "fim":
                linha = por_id.get(evento[1])
                if linha:
                    linha["estado"] = "ok" if evento[2] else "erro"
                    linha["duracao"] = time.perf_counter() - linha["t0"]
            elif tipo == "llm":
                llm_ativo = evento[1]
            elif tipo == "fim_geral":
                terminou = True
            try:
                evento = fila.get_nowait()
            except queue.Empty:
                evento = None

        rodando = [l for l in linhas if l["estado"] == "rodando"]
        if rodando:
            atividade = rodando[-1]["texto"]
        else:
            atividade = "Raciocinando" if llm_ativo else "Processando"
        atualizar(linhas, atividade, time.perf_counter() - inicio)

    if "erro" in saida:
        raise saida["erro"]
    return saida["resultado"]
