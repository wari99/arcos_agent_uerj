import logging
import time
import warnings

warnings.filterwarnings("ignore", message=".*additionalProperties.*")
logging.getLogger("langchain_google_vertexai.functions_utils").setLevel(logging.ERROR)

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage

from agents.agent import agent_memory
from agents.tools.commons.core import get_logger
from agents.tools.commons.utils import limpar_pasta_temporaria_manual
from db.sessions import get_session_manager

logger = get_logger("supervisor")
session_manager = get_session_manager()
SESSION_ID = "arcos_user_default"


def main():
    print("💬💬💬 Bem-vindo ao ARCOS-RJ! Digite '/sair' para encerrar.\n")

    while True:
        try:
            pergunta = input("🟡🟡🟡 Você: ").strip()

            if pergunta.lower() == "/sair":
                print("💬💬💬 ARCOS-RJ: Até logo!")

                try:
                    limpeza_result = limpar_pasta_temporaria_manual()
                    print(
                        "ARCOS-RJ:",
                        limpeza_result.get("mensagem", "Limpeza concluída!"),
                    )
                except ImportError as e:
                    print(f"ARCOS-RJ: Erro no import da limpeza: {e}")
                except Exception as e:
                    print(f"ARCOS-RJ: Erro na limpeza: {e}")

                try:
                    session_manager.export_session_by_id(SESSION_ID)
                    print("💾 Sessão exportada com sucesso!")
                except Exception as e:
                    print(f"Erro ao exportar sessão: {e}")

                break

            logger.info(
                f"pergunta recebida, supervisor analisando | pergunta: {pergunta[:300]}"
            )
            inicio = time.perf_counter()
            resultado = agent_memory.invoke(
                {"messages": [HumanMessage(content=pergunta)]},
                config={"configurable": {"thread_id": SESSION_ID}},
            )
            logger.info(f"supervisor concluiu em {time.perf_counter() - inicio:.1f}s")

            resposta = resultado["messages"][-1].text.strip()

            if not resposta:
                print(
                    "⚠️ ARCOS-RJ: Não consegui gerar uma resposta. Tente reformular a pergunta."
                )
                continue

            session_manager.add_message(SESSION_ID, "user", pergunta)
            session_manager.add_message(SESSION_ID, "ai", resposta)

            print("💬💬💬 ARCOS-RJ:", resposta)

        except KeyboardInterrupt:
            print("\n\nCTRL + C Encerrando...")

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
            print(f"❌ Erro: {e}")


if __name__ == "__main__":
    main()
