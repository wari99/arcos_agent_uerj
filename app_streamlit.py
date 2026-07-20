import streamlit as st
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import agent_memory


st.set_page_config(
    page_title="ARCOS Agent",
    page_icon="random", # streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app
    layout="wide",
    #menu_items={}
)


st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #0E1117 !important;
    color: #FAFAFA !important;
}
.stTextInput input {
    background-color: #1E1E1E !important;
    color: white !important;
}
.chat-message {
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    background-color: #1E1E1E;
}
.user-msg { border-left: 4px solid #4FC3F7; }
.agent-msg { border-left: 4px solid #81C784; }
.error-msg { border-left: 4px solid #E57373; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"streamlit-{datetime.now().strftime('%Y%m%d%H%M%S')}"

if "pending_user_input" not in st.session_state:
    st.session_state.pending_user_input = None

st.title("ARCOS-RJ")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='chat-message user-msg'><b>Você:</b><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )

    elif msg["role"] == "assistant":
        st.markdown(
            f"<div class='chat-message agent-msg'><b>ARCOS:</b><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )
        if "grafico" in msg and msg["grafico"]:
            if os.path.exists(msg["grafico"]):
                st.image(msg["grafico"], use_container_width=True)

    elif msg["role"] == "error":
        st.markdown(
            f"<div class='chat-message error-msg'><b>Erro:</b><br>{msg['content']}</div>",
            unsafe_allow_html=True
        )

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Digite...", label_visibility="collapsed")
    submitted = st.form_submit_button("Enviar")

if submitted and user_input:
    timestamp = datetime.now().strftime("%H:%M:%S")

    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": timestamp
    })

    st.session_state.pending_user_input = user_input
    st.rerun()

if st.session_state.pending_user_input:
    user_input = st.session_state.pending_user_input
    st.session_state.pending_user_input = None

    timestamp = datetime.now().strftime("%H:%M:%S")

    with st.spinner("Processando..."):
        try:
            resultado = agent_memory.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config={"configurable": {"thread_id": st.session_state.thread_id}}
            )

            resposta = str(resultado["messages"][-1].content)

            grafico_path = None
            if ".png" in resposta:
                palavras = resposta.split()
                for palavra in palavras:
                    if palavra.endswith(".png") and os.path.exists(palavra):
                        grafico_path = palavra
                        break

            st.session_state.messages.append({
                "role": "assistant",
                "content": resposta,
                "timestamp": timestamp,
                "grafico": grafico_path
            })

        except Exception as e:
            st.session_state.messages.append({
                "role": "error",
                "content": str(e),
                "timestamp": timestamp
            })

    st.rerun()