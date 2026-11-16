# regex que casa qualquer caractere que NÃO seja letra minúscula ou número.
# Usado para limpar nomes de coluna encontrados: "Qtd. Transações" -> "qtdtransacoes"
_PADRAO_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]")

# qtd de valores parecidos devolver quando o filtro não acha nada
LIMITE_SUGESTOES_DE_VALORES = 20

"""
Funções de apoio compartilhadas pelas operações (_operacoes_*.py):
tudo que lida com NOMES DE COLUNA e com BUSCA DE VALORES dentro de uma coluna.

Funções públicas:
- normalizar_texto: tira acentos e põe em minúsculas
- resolver_coluna: acha a coluna real quando o nome vem levemente errado ("Qtde" em vez de "Qtd.")
- validar_coluna: confere se a coluna existe e monta o erro padrão
- mascara_por_valor / filtrar_por_valor: linhas em que a coluna CONTÉM um valor (sem acento, sem maiúsculas)
- sugerir_valores: valores parecidos com o procurado, para ajudar quando nada casa
"""

import difflib
import logging
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import re

logger = logging.getLogger(__name__)

@lru_cache(maxsize=8192)
def normalizar_texto(texto: str) -> str:
    """
    Tira os acentos, passa para minúsculas e remove espaços das pontas.
    Exemplo: "  ÔNIBUS Intermunicipal " -> "onibus intermunicipal"

    Espera receber TEXTO: quem chama converte antes com str() se o valor puder ser outra coisa
    (número, None...).

    O @lru_cache guarda os resultados já calculados: se o mesmo texto aparecer de novo,
    a resposta sai da memória em vez de ser recalculada (isso deixa o filtro bem mais rápido).
    """
    texto_decomposto = unicodedata.normalize("NFKD", texto)

    letras_sem_acento = []

    for caractere in texto_decomposto:
        categoria = unicodedata.category(caractere)
        if not categoria.startswith("M"):
            letras_sem_acento.append(caractere)

    texto_sem_acento = "".join(letras_sem_acento)

    return texto_sem_acento.lower().strip()

def simplificar_nome_de_coluna(nome) -> str:
    """
    Deixa só letras minúsculas e números, sem acento, espaço ou pontuação. Serve para comparar nomes de coluna que se parecem.

    Exemplos:
        "Qtd. Transações"  -> "qtdtransacoes"
        "Qtde Transações"  -> "qtdetransacoes"
        "Nº Carro"         -> "nocarro"   (o símbolo "º" é decomposto na letra "o")
    """
    sem_acento = normalizar_texto(str(nome))  # str(): o nome da coluna pode ser um número
    return _PADRAO_NAO_ALFANUMERICO.sub("", sem_acento)

def resolver_coluna(df: pd.DataFrame, nome):
    """
    Descobre qual coluna real do DataFrame corresponde ao nome informado pelo modelo. O modelo às vezes erra um pouco o nome ("Qtde Transações" em vez de "Qtd. Transações").

    Tenta, nesta ordem:
      1. O nome já existe exatamente igual         -> devolve o próprio nome.
      2. Existe igual depois de "simplificar"      -> devolve a coluna real.
      3. Existe parecido (mais de 80% de acerto)   -> devolve a coluna mais parecida.
      4. Nada se parece                            -> devolve o nome original, sem mudar.
         (quem chamou percebe depois que a coluna não existe e devolve o erro)
    """
    if not nome or nome in df.columns:
        return nome

    # monta uma tabela p consulta: nome simplificado -> nome real da coluna.
    coluna_real_por_nome_simplificado = {}
    for coluna_real in df.columns:
        nome_simplificado = simplificar_nome_de_coluna(coluna_real)
        coluna_real_por_nome_simplificado[nome_simplificado] = coluna_real

    nome_procurado = simplificar_nome_de_coluna(nome)

    #igual depois de simplificar
    if nome_procurado in coluna_real_por_nome_simplificado:
        coluna_escolhida = coluna_real_por_nome_simplificado[nome_procurado]
    else:
        # procura o nome mais parecido (cutoff=0.8 significa 80% de semelhança)
        candidatos = list(coluna_real_por_nome_simplificado.keys())
        parecidos = difflib.get_close_matches(nome_procurado, candidatos, n=1, cutoff=0.8)

        if not parecidos:
            return nome

        coluna_escolhida = coluna_real_por_nome_simplificado[parecidos[0]]

    logger.info(f"Coluna '{nome}' resolvida para '{coluna_escolhida}'")
    return coluna_escolhida


def validar_coluna(df: pd.DataFrame, nome, mensagem: str, **extras) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """
    Confere se a coluna existe (corrigindo pequenos erros de digitação com resolver_coluna).

    Devolve sempre DOIS valores:
      - o nome da coluna (já corrigido, se foi o caso);
      - None se a coluna existe, ou um dicionário de erro se não existe.

    Parâmetros:
      mensagem: texto do erro. O "{}" é trocado pelo nome da coluna. Ex.: "Coluna '{}' não encontrada"
      extras:   campos adicionais para incluir no erro (ex.: coluna_fornecida="Linha").

    Como usar:
        coluna, erro = validar_coluna(df, coluna, "Coluna '{}' não encontrada")
        if erro:
            return erro
    """
    nome = resolver_coluna(df, nome)

    if not nome or nome in df.columns:
        return nome, None

    logger.error(f"Coluna '{nome}' não existe")

    erro = {"erro": mensagem.format(nome)}
    erro.update(extras)
    erro["colunas_disponiveis"] = list(df.columns)
    erro["sucesso"] = False
    return nome, erro

def mascara_por_valor(df: pd.DataFrame, coluna: str, valor) -> Tuple[pd.Series, List[str]]:
    """
    Marca (True/False) as linhas em que a coluna CONTÉM o valor procurado.
    A busca é parcial, ignora acento e ignora maiúsculas/minúsculas.
    Exemplo: o valor "idoso" encontra "7001 - Idoso".

    Truque de velocidade: em vez de comparar linha por linha (podem ser milhões),
    comparamos só os valores DISTINTOS da coluna (geralmente poucos) e depois
    marcamos todas as linhas que têm algum desses valores.

    Devolve dois resultados:
      - uma série de True/False, uma por linha do DataFrame;
      - a lista (em texto) dos valores distintos que casaram.
    """
    coluna_como_texto = df[coluna].astype(str)
    procurado = normalizar_texto(str(valor))

    valores_que_casaram = []
    for valor_distinto in coluna_como_texto.unique():
        valor_normalizado = normalizar_texto(valor_distinto)
        if procurado in valor_normalizado:
            valores_que_casaram.append(valor_distinto)

    linha_casou = coluna_como_texto.isin(valores_que_casaram)

    return linha_casou, valores_que_casaram


def filtrar_por_valor(df: pd.DataFrame, coluna: str, valor) -> Tuple[pd.DataFrame, List[str]]:
    """
    Igual a mascara_por_valor, mas já devolve o DataFrame só com as linhas que casaram
    (e a lista dos valores distintos que casaram).
    """
    linha_casou, valores_que_casaram = mascara_por_valor(df, coluna, valor)
    return df[linha_casou], valores_que_casaram


def sugerir_valores(valores, procurado, limite: int = LIMITE_SUGESTOES_DE_VALORES) -> list:
    """
    Quando um filtro não acha nenhuma linha, ajuda o modelo a corrigir o pedido
    devolvendo os valores da coluna mais PARECIDOS com o que foi procurado.

    - Se a coluna tem poucos valores distintos (até o limite), devolve todos, na ordem original.
    - Se tem muitos (ex.: 414 operadoras), devolve só os mais parecidos, em vez de despejar tudo.
    """
    valores = list(valores)
    if len(valores) <= limite:
        return valores

    valor_original_por_texto = {}
    for valor_distinto in valores:
        valor_original_por_texto[str(valor_distinto)] = valor_distinto

    textos_parecidos = difflib.get_close_matches(
        str(procurado), list(valor_original_por_texto.keys()), n=limite, cutoff=0.0
    )

    sugestoes = []
    for texto in textos_parecidos:
        sugestoes.append(valor_original_por_texto[texto])
    return sugestoes
