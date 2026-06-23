"""
Configurações globais e constantes da aplicação.
Centraliza os valores reutilizáveis em múltiplos módulos.
"""

from datetime import datetime

# ========== DEFINIÇÃO DE INFORMAÇÕES TEMPORAIS ==========

AGORA = datetime.now()
ANO_ATUAL = AGORA.year
MES_ATUAL = AGORA.month
DATA_FORMATADA = AGORA.strftime("%d de %B de %Y")

MESES_PT_BR = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

MES_ATUAL_NOME = MESES_PT_BR[MES_ATUAL]

# ========== DEFINIÇÃO DAS FAIXAS HORÁRIAS (TURNOS) ==========

FAIXAS_HORARIAS = {
    0: {
        "nome": "Madrugada",
        "intervalo": "00:01 até 06:00",
        "inicio": 0,
        "fim": 6,
        "descricao": "Turno da Madrugada (após meia-noite até amanhecer)"
    },
    1: {
        "nome": "Manhã",
        "intervalo": "06:01 até 12:00",
        "inicio": 6,
        "fim": 12,
        "descricao": "Turno da Manhã"
    },
    2: {
        "nome": "Tarde",
        "intervalo": "12:01 até 18:00",
        "inicio": 12,
        "fim": 18,
        "descricao": "Turno da Tarde"
    },
    3: {
        "nome": "Noite",
        "intervalo": "18:01 até 00:00",
        "inicio": 18,
        "fim": 23,
        "descricao": "Turno da Noite"
    }
}

# ========== OPERAÇÕES DISPONÍVEIS ==========

OPERACOES_DISPONIVEIS = [
    "contar_linhas",
    "mostrar_colunas",
    "preview",
    "contar_por_valor",
    "agrupar_e_somar",
    "filtrar_por_turno",
    "contar_por_turno",
    "comparar_por_turno",
    "agrupar_por_gratuidade_e_turno",
    "media",
    "soma",
    "max",
    "min"
]

# ========== CONFIGURAÇÕES DE FORMATO E ENCODINGS ==========

SEPARADORES_CSV = [";", ",", "\t", "|"]
ENCODINGS_SUPORTADOS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
ENCODING_PADRAO = 'utf-8'        

# ========== CORES PARA GRÁFICOS ==========

CORES_GRAFICOS = {
    "primarias": ['#ace7ff', '#ffb5e8', '#bffcc6', '#a79aff', '#f48a94'],
    "neutras": ['#8c564b', '#fff7d2', '#7f7f7f'],
    "destaque": '#ff6b6b'
}

# ========== VÁRIAVEIS DE LIMITES E CONFIGURAÇÕES ==========

LIMITE_LINHAS_PREVIEW = 5
LIMITE_ARQUIVOS_LISTAR = 10
TAMANHO_MAXIMO_CACHE_MB = 1000  
TIMEOUT_DOWNLOAD_SEGUNDOS = 300
TIMEOUT_REQUISICAO = 60          # em segundos

AMOSTRA_DETECCAO = 2000          # primeiros N bytes para detectar padrão
LIMIAR_SEPARADOR = 10            # mínimo de ocorrências para considerar válido
MAX_ARQUIVOS = 5                 # máximo de arquivos a processar

# ========== DETECÇÃO DE PADRÕES EM NOMES DE ARQUIVOS ==========

LIMIARES_DETECCAO = {
    'prefixo_substring': 0.30,
    'prefixo_separador': 0.15,
    'min_frequencia': 1,
    'min_sequencias': 2,
}

REGEX_PATTERNS = {
    'ano': r'\b(19|20|21)\d{2}\b',
    'mes': r'\b(0[1-9]|1[0-2])\b',
    'dia': r'\b([0-2][0-9]|3[01])\b',
    'numero': r'\b\d+\b',

    'data_filtro': r'(\d{4})[_\-](\d{2})([_\-](\d{2}))?',           
    'data_completa_nome': r'\d{4}[_\-]\d{2}[_\-]\d{2}', 
}

REGEX_REPLACEMENTS = {
    'ano': 'YYYY',
    'mes': 'MM',
    'dia': 'DD',
    'numero': 'NUM'
}