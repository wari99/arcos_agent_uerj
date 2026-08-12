import warnings
import logging
warnings.filterwarning("ignore", message=".*additionalProperties")
logging.getLogger("langchain_google_vertexai.functions_utils").setLevel(logging.ERROR)

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

from langchain_google_vertexai import ChatVertexAI
from langchain.agents import create_agent, AgentState
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from prompts.commons.utils import load_prompt_from_markdown
from tools.get_current_date import get_current_date
from tools.listar_bases import listar_bases
from tools.buscar_infos_base import buscar_infos_base
from tools.listar_recursos_da_base import listar_recursos_da_base
from tools.baixar_arquivo_dados import baixar_arquivo_dados
from tools.gerenciar_cache_sessao import gerenciar_cache_sessao
from tools.commons.utils import limpar_pasta_temporaria_manual
from tools.analisar_dados_arquivo import analisar_dados_arquivo
from tools.gerar_graficos import gerar_graficos  

load_dotenv()

PROMPTS_DIR = Path(__file__).parent / "prompts"
ROOT_PROMPT = load_prompt_from_markdown(str(PROMPTS_DIR))

@dataclass
class Context:
    user_id: str

model = ChatVertexAI(
    model_name=os.getenv("ROOT_AGENT_MODEL"),  
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),                     
    location=os.getenv("GOOGLE_CLOUD_LOCATION"),   
    temperature=0.5,
)

agent = create_agent(
    model=model,
    context_schema=Context,
    system_prompt=ROOT_PROMPT, 
    tools=[
        listar_bases,           
        buscar_infos_base,      
        listar_recursos_da_base,
        baixar_arquivo_dados,        
        analisar_dados_arquivo, 
        gerenciar_cache_sessao,  
        gerar_graficos,
        get_current_date              
    ],
)

# ============================================================
# WIP: STATE GRAPH DO AGENTE
# ============================================================
graph = StateGraph(AgentState)

graph.add_node("inicio", agent)
graph.set_entry_point("inicio")

checkpointer = InMemorySaver()

agent_memory = graph.compile(checkpointer=checkpointer)
# ============================================================
# 
# ============================================================


print("💬💬💬 Bem-vindo ao ARCOS-RJ! Digite '/sair' para encerrar.\n")

while True:
    pergunta = input("🟡🟡🟡 Você: ").strip()

    if pergunta.lower() == "/sair":
        print("💬💬💬 ARCOS-RJ: Até logo!")

        try:
            limpeza_result = limpar_pasta_temporaria_manual()  
            print("ARCOS-RJ:", limpeza_result.get('mensagem', 'Limpeza concluída!'))
        except ImportError as e:
            print(f"ARCOS-RJ: Erro no import da limpeza: {e}")
        except Exception as e:
            print(f"ARCOS-RJ: Erro na limpeza: {e}")
        break
    try:
        resultado = agent_memory.invoke(
            {"messages": [{"role": "user", "content": pergunta}]}, config={"thread_id": "1"}
        )

        mensagens = resultado["messages"][-1].content

        if isinstance(mensagens, list) and len(mensagens) > 0 and "text" in mensagens[0]:
            resposta = mensagens[0]["text"]
        else:
            resposta = str(mensagens)

        print("💬💬💬 ARCOS-RJ:", resposta)
        
    except KeyboardInterrupt:
        print("\nCTRL+C - Encerrando...")
        
        try:
            resultado_limpeza = limpar_pasta_temporaria_manual() 
            print(f"🗑️ {resultado_limpeza.get('mensagem', 'Limpeza concluída!')}")
        except ImportError as e:
            print(f"🗑️ Erro no import da limpeza: {e}")
        except Exception as e:
            print(f"🗑️ Erro na limpeza: {e}")
        
        break
    except Exception as e:
        print(f"Erro: {e}")