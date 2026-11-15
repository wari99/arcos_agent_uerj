"""Leitura de uma página como imagem pelo Gemini (OCR, tabelas difíceis e gráficos)."""
import base64

from langchain_core.messages import HumanMessage

from agents.model import model

INSTRUCAO_BASE = """Você está lendo a página {pagina} de um documento oficial, em português do Brasil.
Faça uma transcrição fiel do que está VISÍVEL, sem inventar nada:
- Texto: transcreva na ordem de leitura, sem linhas em branco extras.
- Tabelas: reproduza em Markdown, mantendo os números exatamente como aparecem.
- Gráficos: diga o tipo (barras, linhas, pizza...), o título, os eixos, as séries ou categorias e TODOS os valores
  escritos no gráfico (rótulos). Se for preciso estimar um valor pela altura de uma barra ou posição de um ponto,
  escreva "aprox." ao lado. Descreva a tendência em uma frase.
- O que estiver ilegível ou cortado: escreva [ilegível]. Não complete por dedução."""


def descrever_pagina(png: bytes, pagina: int, pergunta: str = "") -> str:
    instrucao = INSTRUCAO_BASE.format(pagina=pagina)
    if pergunta and pergunta.strip():
        instrucao += f"\n\nFoque no que ajuda a responder: {pergunta.strip()}"

    b64 = base64.b64encode(png).decode()
    mensagem = HumanMessage(
        content=[
            {"type": "text", "text": instrucao},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]
    )
    return model.invoke([mensagem]).text.strip()
