import sqlite3
from langchain_community.chat_message_histories import SQLChatMessageHistory
from tools.commons.core import logger
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "sessions.db"
DB_URI = f"sqlite:///{DB_PATH}"
SESSION_TIMEOUT = 48

logger.info(f"Banco: {DB_PATH} | Timeout: {SESSION_TIMEOUT}h")


class SessionManager:
    """Gerenciamento das sessões de conversa com o agente.
    
    Funcionalidades:
    - Recupera históricos de chat
    - Limpa sessões antigas (atrelado a SESSION_TIMEOUT, default 48 (horas))
    - Inicia o banco de dados
    """
    
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self.connection_string = f"sqlite:///{db_path}"
        self._create_table()
    
    def _create_table(self):
        """
        Criação da tabela com a estrutura correta, caso ela ainda não exista.
        """

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            logger.debug("Tabela message_store garantida")
        except Exception as e:
            logger.error(f"Erro ao criar tabela: {e}")
    
    def get_history(self, session_id: str) -> SQLChatMessageHistory:
        """Retorna o histórico de uma sessão.
        
        Limpa sessões antigas (mais de 48h) antes de retornar.
        """
        self.remove_expired_sessions()
        return SQLChatMessageHistory(
            session_id=session_id,
            connection_string=self.connection_string,
            table_name="message_store"
        )
    
    def clear_session(self, session_id: str) -> bool:
        """Apaga todas as mensagens de uma sessão específica."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "DELETE FROM message_store WHERE session_id = ?", 
                (session_id,)
            )
            conn.commit()
            conn.close()
            logger.info(f"Sessão limpa: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar sessão: {e}")
            return False
    
    def remove_expired_sessions(self):
        """Remove mensagens com mais de 48 horas."""
        try:
            cutoff = datetime.now() - timedelta(hours=SESSION_TIMEOUT)
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "DELETE FROM message_store WHERE created_at < ?",
                (cutoff.isoformat(),)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    @staticmethod
    def get_uri() -> str:
        """Retorna a URI do banco para usar em componentes LangChain."""
        return DB_URI


# criacao da instancia uma unica vez quando o arquivo é importado
_manager = SessionManager()
logger.info("SessionManager inicializado")

def get_session_manager() -> SessionManager:
    """Retorna a instância do gerenciador de sessões."""
    return _manager