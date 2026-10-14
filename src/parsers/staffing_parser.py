"""
Parser Especializado de Crew Staffing do SIPCAP.
"""
import re
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd

from ..domain.enums import TipoStaffingEnum, FrotaEnum
from ..domain.schemas import CrewStaffingItem, PremissasModel
from ..utils.date_utils import normalizar_ano_mes, adicionar_meses


class StaffingParserError(Exception):
    pass


class CrewStaffingParser:
    FROTAS_CONHECIDAS = ["A320", "A330", "ERJ", "ATR", "B737", "737"]

    def __init__(self, frotas_adicionais: Optional[List[str]] = None):
        self.frotas_reconhecidas = sorted(
            list(set(self.FROTAS_CONHECIDAS + (frotas_adicionais or []))),
            key=lambda x: len(x),
            reverse=True
        )

    def extrair_frota_de_texto(self, texto: str) -> Optional[str]:
        texto_upper = texto.upper()
        for f in self.frotas_reconhecidas:
            padrao = rf"\b{re.escape(f)}\b"
            if re.search(padrao, texto_upper):
                return f
        return None

    def interpretar_linha_staffing(
        self,
        career_move: str,
        tipo_declarado: Optional[str] = None,
        contexto_training: Optional[str] = None
    ) -> Tuple[TipoStaffingEnum, Optional[str], str]:
        cm = str(career_move).replace("\xa0", " ").strip()
        cm_upper = cm.upper()
        td_upper = str(tipo_declarado).replace("\xa0", " ").strip().upper() if tipo_declarado else ""
        tr_upper = str(contexto_training).replace("\xa0", " ").strip().upper() if contexto_training else ""

        # 1. Caso de New Hiring
        if "NEW HIRING" in tr_upper or "NEW HIRING" in td_upper or "NEW HIRING" in cm_upper or "NOVO" in cm_upper:
            frota_dest = self.extrair_frota_de_texto(cm)
            if not frota_dest and contexto_training:
                frota_dest = self.extrair_frota_de_texto(contexto_training)
            if not frota_dest and tipo_declarado:
                frota_dest = self.extrair_frota_de_texto(tipo_declarado)

            if not frota_dest:
                raise StaffingParserError(
                    f"Registro de New Hiring '{career_move}' (Training: '{contexto_training}') não permitiu identificar a frota destino."
                )
            return TipoStaffingEnum.NEW_HIRING, None, frota_dest

        # 2. Caso de Transição com Seta (ex: 'FO ERJ -> CA ATR')
        if "->" in cm or "→" in cm:
            delimitador = "->" if "->" in cm else "→"
            partes = cm.split(delimitador)
            origem_raw = partes[0].strip()
            destino_raw = partes[1].strip()

            frota_orig = self.extrair_frota_de_texto(origem_raw)
            frota_dest = self.extrair_frota_de_texto(destino_raw)

            if not frota_dest and contexto_training:
                frota_dest = self.extrair_frota_de_texto(contexto_training)

            if not frota_dest:
                raise StaffingParserError(
                    f"Não foi possível identificar a frota destino na movimentação: '{career_move}'"
                )

            # Mesma frota (ex: FO ERJ -> CA ERJ): Upgrade
            if frota_orig and frota_orig == frota_dest:
                return TipoStaffingEnum.UPGRADE, frota_orig, frota_dest

            # Frotas diferentes (ex: FO ATR -> CA ERJ): Movimentação / Transferência
            if frota_orig and frota_orig != frota_dest:
                return TipoStaffingEnum.MOVIMENTACAO, frota_orig, frota_dest

            if "UPGRADE" in tr_upper or "UPGRADE" in td_upper:
                return TipoStaffingEnum.UPGRADE, frota_orig, frota_dest
            return TipoStaffingEnum.MOVIMENTACAO, frota_orig, frota_dest

        # 3. Posição simples (ex: 'FO A320', 'FO ERJ')
        frota_simples = self.extrair_frota_de_texto(cm)
        if not frota_simples and contexto_training:
            frota_simples = self.extrair_frota_de_texto(contexto_training)

        if frota_simples:
            if "UPGRADE" in tr_upper or "UPGRADE" in td_upper:
                return TipoStaffingEnum.UPGRADE, frota_simples, frota_simples
            return TipoStaffingEnum.NEW_HIRING, None, frota_simples

        raise StaffingParserError(
            f"Formato de Career Move não reconhecido: '{career_move}'. "
            f"Esperado padrão com seta ou New Hiring."
        )

    def parse_dataframe(
        self,
        df: pd.DataFrame,
        premissas: PremissasModel
    ) -> List[CrewStaffingItem]:
        if df.empty:
            return []

        df_proc = df.copy()

        # 1. Identificar coluna Training
        coluna_training = None
        for col in df_proc.columns:
            if str(col).strip().lower() in ["training", "treinamento", "programa"]:
                coluna_training = col
                break

        if coluna_training:
            df_proc[coluna_training] = df_proc[coluna_training].ffill()

        # 2. Identificar coluna Career Move
        colunas_possiveis = ["career_move", "career move", "careermove", "fluxo", "movimentacao", "descricao"]
        coluna_move = None
        for col in df_proc.columns:
            if str(col).strip().lower() in colunas_possiveis:
                coluna_move = col
                break

        if not coluna_move:
            for col in df_proc.columns:
                if col != coluna_training and (df_proc[col].dtype == object or pd.api.types.is_string_dtype(df_proc[col])):
                    coluna_move = col
                    break

        if not coluna_move:
            raise StaffingParserError(
                f"Coluna de identificação de Career Move não encontrada. Colunas: {list(df_proc.columns)}"
            )

        coluna_tipo = None
        for col in df_proc.columns:
            if str(col).strip().lower() in ["tipo", "tipo_movimentacao", "categoria", "status"]:
                coluna_tipo = col
                break

        # 3. Identificar colunas temporais
        colunas_meses = []
        for col in df_proc.columns:
            if col in [coluna_training, coluna_move, coluna_tipo]:
                continue
            try:
                ano_mes_norm = normalizar_ano_mes(str(col))
                colunas_meses.append((col, ano_mes_norm))
            except ValueError:
                continue

        if not colunas_meses:
            raise StaffingParserError("Nenhuma coluna de mês reconhecida no arquivo de Crew Staffing.")

        itens: List[CrewStaffingItem] = []
        offset = premissas.OFFSET_CHEQUE_MOVIMENTACAO
        fator_cheques = getattr(premissas, "CHEQUES_POR_TRIPULANTE_STAFFING", 1)

        for idx, row in df_proc.iterrows():
            cm_val = row[coluna_move]
            if pd.isna(cm_val) or str(cm_val).strip() == "":
                continue

            tipo_val = row[coluna_tipo] if coluna_tipo and not pd.isna(row[coluna_tipo]) else None
            training_val = row[coluna_training] if coluna_training and not pd.isna(row[coluna_training]) else None

            tipo_evento, frota_orig, frota_dest = self.interpretar_linha_staffing(
                str(cm_val), tipo_val, training_val
            )

            for col_orig, ano_mes_entrada in colunas_meses:
                val = row[col_orig]
                if pd.isna(val):
                    continue

                try:
                    qtd = int(float(val))
                except (ValueError, TypeError):
                    continue

                if qtd <= 0:
                    continue

                ano_mes_cheque = adicionar_meses(ano_mes_entrada, offset)
                cheques_gerados = qtd * int(fator_cheques)

                cm_str = str(cm_val).replace("\xa0", " ").strip()
                if "CA" in cm_str.upper():
                    funcao_tripulante = "Comandante"
                elif "FO" in cm_str.upper():
                    funcao_tripulante = "Copiloto"
                else:
                    funcao_tripulante = "Piloto"

                item = CrewStaffingItem(
                    career_move_original=cm_str,
                    tipo_evento=tipo_evento,
                    frota_origem=frota_orig,
                    frota_destino=frota_dest,
                    ano_mes_entrada=ano_mes_entrada,
                    mes_origem=ano_mes_entrada,
                    funcao=funcao_tripulante,
                    qtd_tripulantes=qtd,
                    offset_meses=offset,
                    ano_mes_cheque=ano_mes_cheque,
                    cheques_gerados=cheques_gerados
                )
                itens.append(item)

        return itens

    def consolidar_para_auditoria(self, itens: List[CrewStaffingItem]) -> pd.DataFrame:
        if not itens:
            return pd.DataFrame(columns=[
                "frota_destino", "ano_mes_cheque", "tipo_evento", "qtd_tripulantes", "cheques_gerados"
            ])

        dados = [
            {
                "frota_destino": it.frota_destino,
                "ano_mes_cheque": it.ano_mes_cheque,
                "tipo_evento": it.tipo_evento.value,
                "qtd_tripulantes": it.qtd_tripulantes,
                "cheques_gerados": it.cheques_gerados
            }
            for it in itens
        ]
        df = pd.DataFrame(dados)
        return df.groupby(["frota_destino", "ano_mes_cheque", "tipo_evento"], as_index=False).sum()