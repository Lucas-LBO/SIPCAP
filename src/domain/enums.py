"""
Enums de Domínio do SIPCAP.
Define frotas, tipos de funções, categorias e status RAG.
"""
from enum import Enum


class FrotaEnum(str, Enum):
    ERJ = "ERJ"
    A320 = "A320"
    ATR = "ATR"
    A330 = "A330"


class CategoriaFuncaoEnum(str, Enum):
    AERONAUTA = "Aeronauta"
    AEROVIARIO = "Aeroviario"


class TipoStaffingEnum(str, Enum):
    NEW_HIRING = "New Hiring"
    UPGRADE = "Upgrade"
    MOVIMENTACAO = "Movimentacao"


class StatusRAGEnum(str, Enum):
    VERDE = "Verde"
    AMARELO = "Amarelo"
    VERMELHO = "Vermelho"