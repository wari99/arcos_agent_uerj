import sqlite3
import json
from langchain_community.chat_message_histories import SQLChatMessageHistory
from tools.commons.core import logger
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "sessions.db"
EXPORTS_DIR = DB_DIR / "exports"
DB_URI = f"sqlite:///{DB_PATH}"

logger.info(f"Banco: {DB_PATH}")

class SessionManager:
    """Gerencia sessões de conversa.
    
    Responsabilidades:
    - Recuperar históricos de chat
    - Armazenar mensagens indefinidamente (SEM deletar)
    - Exportar sessões para arquivos .db separados com timestamp
    - Inicializar o banco de dados
    """
    
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self.connection_string = f"sqlite:///{db_path}"
        self._create_table()
    
    def _create_table(self):
        """Cria a tabela com a estrutura correta se não existir."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.debug("Tabela message_store garantida")
        except Exception as e:
            logger.error(f"Erro ao criar tabela: {e}")
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Adiciona uma mensagem com timestamp manualmente."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            message_data = {
                "type": "human" if role == "user" else "ai",
                "data": {
                    "content": content
                }
            }
            
            cursor.execute(
                "INSERT INTO message_store (session_id, message, created_at) VALUES (?, ?, ?)",
                (session_id, json.dumps(message_data), datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {e}")
            return False
    
    def get_history(self, session_id: str) -> SQLChatMessageHistory:
        return SQLChatMessageHistory(
            session_id=session_id,
            connection_string=self.connection_string,
            table_name="message_store"
        )
    
    def clear_session(self, session_id: str) -> bool:
        """
        Apaga todas as mensagens de uma sessão específica.
        """
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
    
    def export_session_by_id(self, session_id: str) -> bool:
        """
        Exporta uma sessão específica para um arquivo .db separado com timestamp.
        """

        try:
            EXPORTS_DIR.mkdir(exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message, created_at FROM message_store WHERE session_id = ? ORDER BY rowid",
                (session_id,)
            )
            messages = cursor.fetchall()
            conn.close()
            
            if not messages:
                logger.warning(f"Nenhuma mensagem encontrada para sessão: {session_id}")
                return False
            
            timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            filename = f"sessao_{session_id}_{timestamp}.db"
            export_path = EXPORTS_DIR / filename
            
            export_conn = sqlite3.connect(str(export_path))
            export_cursor = export_conn.cursor()
            
            export_cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            for message, created_at in messages:
                export_cursor.execute(
                    "INSERT INTO message_store (session_id, message, created_at) VALUES (?, ?, ?)",
                    (session_id, message, created_at)
                )
            
            export_conn.commit()
            export_conn.close()
            
            logger.info(f"Sessão exportada: {filename} ({len(messages)} mensagens)")
            return True
            
        except Exception as e:
            logger.error(f"Erro exportar sessão {session_id}: {e}")
            return False
    
    @staticmethod
    def get_uri() -> str:
        """Retorna a URI do banco para usar em componentes LangChain."""
        return DB_URI

_manager = SessionManager()
logger.info("SessionManager inicializado")
def get_session_manager() -> SessionManager:
    """Retorna a instância do gerenciador de sessões."""
    return _manager