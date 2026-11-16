import streamlit as st
import os
import sys
import yaml
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent import agent_memory
from ui.streamlit_progress import executar_com_progresso
from db.sessions import get_session_manager
from agents.tools.commons.utils import limpar_pasta_temporaria_manual

session_manager = get_session_manager()

# Carregar configurações do YAML
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()

# Configurar página
st.set_page_config(
    page_title=config["streamlit"]["page_title"],
    page_icon=config["streamlit"]["page_icon"],
    layout=config["streamlit"]["layout"],
)

# Aplicar CSS dinamicamente
# o toggle usa key (id estável) e fica desabilitado enquanto o agente responde: mexer num widget durante a
# execução faz o Streamlit reiniciar o script e interrompe a resposta
with st.sidebar:
    modo_claro = st.toggle(
        "Modo Claro",
        key="modo_claro",
        disabled=bool(st.session_state.get("pending_user_input")),
    )
st.session_state.theme_mode = "light" if modo_claro else "dark"

theme = config["theme"][st.session_state.theme_mode]
css_style = f"""
<style>
html, body, [class*="css"], .stApp, [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stBottom"] > div {{
    background-color: {theme["background_color"]} !important;
    color: {theme["text_color"]} !important;
}}
.stTextInput input {{
    background-color: {theme["input_bg"]} !important;
    color: {theme["input_text"]} !important;
}}
[data-testid="stChatInput"] textarea, .stApp p, .stApp h1, .stApp label, .chat-message, .chat-message b {{
    color: {theme["text_color"]} !important;
}}
.stButton > button, [data-testid="stFormSubmitButton"] > button {{
    background-color: {theme["button_bg"]} !important;
    color: {theme["button_text"]} !important;
    border: 1px solid {theme["borders"]["user"]} !important;
}}
.stButton > button p, [data-testid="stFormSubmitButton"] > button p {{
    color: {theme["button_text"]} !important;
}}
[data-testid="stStatus"], [data-testid="stExpander"] {{
    background-color: {theme["status_bg"]} !important;
    border: 1px solid {theme["borders"]["user"]} !important;
    border-radius: 10px;
}}
[data-testid="stStatus"] details, [data-testid="stStatus"] summary,
[data-testid="stExpander"] details, [data-testid="stExpander"] summary {{
    background-color: {theme["status_bg"]} !important;
}}
[data-testid="stStatus"] *, [data-testid="stExpander"] * {{
    color: {theme["text_color"]} !important;
}}
.stApp code, .stApp pre, [data-testid="stCode"], [data-testid="stCode"] pre {{
    background-color: {theme["code_bg"]} !important;
    color: {theme["code_text"]} !important;
}}
.chat-message {{
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    background-color: {theme["input_bg"]};
}}
.user-msg {{ border-left: 4px solid {theme["borders"]["user"]}; }}
.agent-msg {{ border-left: 4px solid {theme["borders"]["agent"]}; }}
.error-msg {{ border-left: 4px solid {theme["borders"]["error"]}; }}
</style>
"""

st.markdown(css_style, unsafe_allow_html=True)

# Inicializar session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"streamlit-{datetime.now().strftime('%Y%m%d%H%M%S')}"

if "pending_user_input" not in st.session_state:
    st.session_state.pending_user_input = None

if "session_active" not in st.session_state:
    st.session_state.session_active = True

st.title(config["streamlit"]["page_title"])

# Exibir mensagens do histórico
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='chat-message user-msg'><b>{config['messages']['you']}:</b><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )

    elif msg["role"] == "assistant":
        st.markdown(
            f"<div class='chat-message agent-msg'><b>{config['messages']['arcos']}:</b><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )
        # Mostrar gráfico dentro da coluna de mensagem
        if "grafico" in msg and msg["grafico"]:
            if os.path.exists(msg["grafico"]):
                st.image(msg["grafico"], use_container_width=True)

    elif msg["role"] == "error":
        st.markdown(
            f"<div class='chat-message error-msg'><b>{config['messages']['error_label']}:</b><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )

# Mostrar status da sessão
if not st.session_state.session_active:
    st.info(config["messages"]["session_ended"])

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input(
        config["messages"]["input_placeholder"],
        label_visibility="collapsed",
        disabled=not st.session_state.session_active
    )
    submitted = st.form_submit_button(config["messages"]["button_label"])

if submitted and user_input:
    # Verificar comando /sair
    if user_input.strip().lower() == config["commands"]["exit"]["trigger"]:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": config["messages"]["goodbye"],
            "timestamp": timestamp,
            "grafico": None
        })
        
        # Limpar pasta temporária
        try:
            resultado_limpeza = limpar_pasta_temporaria_manual()
            mensagem_limpeza = resultado_limpeza.get('mensagem', 'Limpeza concluída!')
            cleanup_msg = config["messages"]["cleanup_success"].format(mensagem=mensagem_limpeza)
            st.session_state.messages.append({
                "role": "assistant",
                "content": cleanup_msg,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "grafico": None
            })
        except Exception as e:
            cleanup_error_msg = config["messages"]["cleanup_error"].format(erro=str(e))
            st.session_state.messages.append({
                "role": "error",
                "content": cleanup_error_msg,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
        
        # ✅ ADICIONADO: Exportar sessão ao sair
        try:
            session_manager.export_session_by_id(st.session_state.thread_id)
            export_msg = "💾 Sessão exportada com sucesso!"
            st.session_state.messages.append({
                "role": "assistant",
                "content": export_msg,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "grafico": None
            })
        except Exception as e:
            export_error_msg = f"❌ Erro ao exportar sessão: {str(e)}"
            st.session_state.messages.append({
                "role": "error",
                "content": export_error_msg,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
        
        st.session_state.session_active = False
        st.rerun()
    
    # Verificar comando /reiniciar
    elif user_input.strip().lower() == config["commands"]["restart"]["trigger"]:
        st.session_state.messages = []
        st.session_state.thread_id = f"streamlit-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        st.session_state.session_active = True
        st.rerun()
    
    # Processar mensagem normal
    elif st.session_state.session_active:
        timestamp = datetime.now().strftime("%H:%M:%S")

        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })

        st.session_state.pending_user_input = user_input
        st.rerun()

# Processar resposta do agente
if st.session_state.pending_user_input:
    user_input = st.session_state.pending_user_input
    st.session_state.pending_user_input = None

    timestamp = datetime.now().strftime("%H:%M:%S")

    with st.status(config["messages"]["processing"], expanded=True) as status:
        etapas = st.empty()

        def _atualizar_progresso(linhas, atividade, segundos):
            status.update(label=f"{atividade}… ({segundos:.0f}s)")
            icones = {"rodando": "⏳", "ok": "☑️", "erro": "⚠️"}
            etapas.markdown("\n".join(
                f"{'&nbsp;' * 6 * l['nivel']}{icones[l['estado']]} {l['texto']}"
                + (f" · {l['duracao']:.1f}s" if l["duracao"] is not None else "")
                for l in linhas
            ))

        try:
            resultado = executar_com_progresso(
                agent_memory,
                {"messages": [{"role": "user", "content": user_input}]},
                {"configurable": {"thread_id": st.session_state.thread_id}},
                _atualizar_progresso,
            )

            resposta = resultado["messages"][-1].text.strip()

            grafico_path = None
            
            # Procura por padrões de caminho com .png
            matches = re.findall(r'[/\w\-._]+\.png', resposta)
            
            if matches:
                for match in matches:
                    # Verifica se é um caminho absoluto ou relativo válido
                    if os.path.exists(match):
                        grafico_path = match
                        break
                    # Se for relativo, tenta do diretório atual
                    elif os.path.exists(os.path.join(os.getcwd(), match)):
                        grafico_path = os.path.join(os.getcwd(), match)
                        break

            st.session_state.messages.append({
                "role": "assistant",
                "content": resposta,
                "timestamp": timestamp,
                "grafico": grafico_path
            })
            
            # ✅ ADICIONADO: Salvar no banco com timestamp
            session_manager.add_message(st.session_state.thread_id, "user", user_input)
            session_manager.add_message(st.session_state.thread_id, "ai", resposta)

        except Exception as e:
            status.update(state="error")
            st.session_state.messages.append({
                "role": "error",
                "content": str(e),
                "timestamp": timestamp
            })

    st.rerun()