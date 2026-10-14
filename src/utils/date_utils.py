"""
Utilitários de Manipulação de Datas, Meses e Sazonalidade do SIPCAP.
Suporta normalização flexível de formatos textuais, numéricos e datetime do Excel/Pandas.
"""
import re
from datetime import datetime, date
import calendar
from typing import Tuple, Optional, Any
import pandas as pd


MESES_PT_BR = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
}

MESES_NUM_TO_ABR = {v: k for k, v in MESES_PT_BR.items()}


def normalizar_ano_mes(valor: Any) -> str:
    """
    Normaliza representações diversas de meses para o padrão canônico YYYY-MM.
    Formatos aceitos: '2027-01', 'jan/27', 'fev.-27', 'set.-26', '01/2027', Timestamp, etc.
    """
    if valor is None or (isinstance(valor, float) and (valor != valor)):
        raise ValueError("Mês não pode ser nulo ou vazio.")

    if isinstance(valor, (datetime, date, pd.Timestamp)):
        return f"{valor.year:04d}-{valor.month:02d}"

    v = str(valor).replace("\xa0", " ").strip()
    if not v or v.lower() in ["nat", "nan", "none"]:
        raise ValueError(f"Mês inválido ou vazio: '{valor}'")

    # Formato ISO com data/hora (ex.: '2027-01-01 00:00:00')
    match_datetime_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})[ T].*$", v)
    if match_datetime_iso:
        ano, mes, _ = match_datetime_iso.groups()
        return f"{ano}-{mes}"

    # Formato YYYY-MM-DD
    match_date_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", v)
    if match_date_iso:
        ano, mes, _ = match_date_iso.groups()
        return f"{ano}-{mes}"

    # Formato Canônico exato YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", v):
        return v

    # Formato DD/MM/YYYY
    match_br_full = re.match(r"^\d{1,2}/(\d{2})/(\d{4})(?:[ T].*)?$", v)
    if match_br_full:
        mes, ano = match_br_full.groups()
        return f"{ano}-{mes}"

    # Formato MM/YYYY ou YYYY/MM
    if re.match(r"^\d{2}/\d{4}$", v):
        partes = v.split("/")
        return f"{partes[1]}-{partes[0]}"
    if re.match(r"^\d{4}/\d{2}$", v):
        partes = v.split("/")
        return f"{partes[0]}-{partes[1]}"

    # Formato com abreviação em português: 'jan/27', 'fev-27', 'set.-26', 'abr.-27'
    v_clean = v.lower().replace(".", "").strip()
    match_texto = re.match(r"^([a-z]{3})[/-]?(\d{2,4})$", v_clean)
    if match_texto:
        mes_txt, ano_txt = match_texto.groups()
        if mes_txt in MESES_PT_BR:
            num_mes = MESES_PT_BR[mes_txt]
            ano_num = 2000 + int(ano_txt) if len(ano_txt) == 2 else int(ano_txt)
            return f"{ano_num:04d}-{num_mes:02d}"

    try:
        ts = pd.to_datetime(v)
        if pd.notna(ts):
            return f"{ts.year:04d}-{ts.month:02d}"
    except Exception:
        pass

    raise ValueError(f"Não foi possível normalizar o mês informado: '{valor}'")


normalizar_mes_ano = normalizar_ano_mes


def adicionar_meses(ano_mes: str, offset: int) -> str:
    ano_mes_norm = normalizar_ano_mes(ano_mes)
    ano, mes = map(int, ano_mes_norm.split("-"))
    mes_total = mes + offset
    ano_final = ano + (mes_total - 1) // 12
    mes_final = ((mes_total - 1) % 12) + 1
    return f"{ano_final:04d}-{mes_final:02d}"


def subtrair_meses(ano_mes: str, offset: int) -> str:
    return adicionar_meses(ano_mes, -offset)


def dias_no_mes(ano_mes: str) -> int:
    ano_mes_norm = normalizar_ano_mes(ano_mes)
    ano, mes = map(int, ano_mes_norm.split("-"))
    _, num_dias = calendar.monthrange(ano, mes)
    return num_dias


def formatar_ano_mes_exibicao(ano_mes: str) -> str:
    ano_mes_norm = normalizar_ano_mes(ano_mes)
    ano, mes = map(int, ano_mes_norm.split("-"))
    abr = MESES_NUM_TO_ABR.get(mes, "mes").capitalize()
    ano_curto = ano % 100
    return f"{abr}/{ano_curto:02d}"