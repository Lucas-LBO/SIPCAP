"""
SIPCAP - Configurações Globais e Caminhos dos Arquivos de Entrada.
Padronização nativa em arquivos Excel (.xlsx).
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
TEMPLATES_DIR = DATA_DIR / "templates"
PROCESSED_DIR = DATA_DIR / "processed"

# Caminhos Canônicos dos Arquivos de Entrada (.xlsx)
FILE_PREMISSAS = RAW_DATA_DIR / "tbl_premissas.xlsx"
FILE_SIMULADORES = RAW_DATA_DIR / "tbl_simuladores.xlsx"
FILE_DEMANDA_SLOTS = RAW_DATA_DIR / "tbl_demanda_slots.xlsx"
FILE_CREW_STAFFING = RAW_DATA_DIR / "tbl_crew_staffing.xlsx"
FILE_INSTRUTORES = RAW_DATA_DIR / "tbl_instrutores.xlsx"

# Frotas Suportadas Padrão
FROTAS_PADRAO = ["ERJ", "A320", "ATR", "A330"]

# Formato Canônico de Datas
FORMATO_DATA = "%Y-%m-%d"