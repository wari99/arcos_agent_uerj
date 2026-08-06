import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

from langchain_google_vertexai import ChatVertexAI
from langchain.agents import create_agent, AgentState
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from db.sessions import get_session_manager
from langchain_core.messages import HumanMessage

from prompts.commons.utils import load_prompt_from_markdown
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

session_manager = get_session_manager()
SESSION_ID = "arcos_user_default"


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

messages_session = []

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
        
        try:
            session_manager.export_session_by_id(SESSION_ID)
            print("💾 Sessão exportada com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao exportar sessão: {e}")
        
        break
    
    try:
        messages_session.append(HumanMessage(content=pergunta))
        
        resultado = agent_memory.invoke(
            {
                "messages": messages_session
            },
            config={"thread_id": "1"}
        )

        resposta = resultado["messages"][-1].content
        
        if isinstance(resposta, list) and len(resposta) > 0 and "text" in resposta[0]:
            resposta = resposta[0]["text"]
        else:
            resposta = str(resposta)

        messages_session.append(HumanMessage(content=resposta))
        session_manager.add_message(SESSION_ID, "user", pergunta)
        session_manager.add_message(SESSION_ID, "ai", resposta)
                
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
        
        try:
            session_manager.export_session_by_id(SESSION_ID)
            print("💾 Sessão exportada com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao exportar sessão: {e}")
        
        break
    except Exception as e:
        print(f"Erro: {e}")