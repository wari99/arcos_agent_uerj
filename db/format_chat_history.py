import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "sessions.db"

def format_chat_history():
    """
    Formata histórico chat para facilitar leitura da sessão 
    """

    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute('SELECT message FROM message_store ORDER BY rowid').fetchall()
        conn.close()
        
        print('\n ------- HISTÓRICO DO CHAT ------- ')
        
        if not rows:
            print("Nenhuma mensagem encontrada.")
        else:
            for row in rows:
                try:
                    data = json.loads(row[0])
                    
                    if 'type' in data and 'data' in data:
                        # {"type": "human/ai", "data": {"content": "..."}}
                        msg_type = data['type']
                        content = data['data'].get('content', data['data'].get('text', ''))
                    elif 'content' in data:
                        # {"content": "...", "type": "human/ai"}
                        msg_type = data.get('type', 'human')
                        content = data['content']
                    else:
                        content = str(data)
                        msg_type = 'unknown'
                    
                    prefix = 'User' if msg_type == 'human' else 'ARCOS'
                    print(f'\n{prefix}:\n  {content}\n')
                    
                except json.JSONDecodeError:
                    print(f'\nErro JSONDecode - {row[0]}\n')
        
    except Exception as e:
        print(f"Erro acesso sqlite: {e}")

if __name__ == "__main__":
    format_chat_history()