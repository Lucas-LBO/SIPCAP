"""
Módulo de Leitura e Validação de Dados (Data Loader) do SIPCAP.
Carrega e valida os arquivos de entrada (CSV / Excel):
- tbl_instrutores
- tbl_demanda_slots
- tbl_simuladores
- tbl_crew_staffing
- tbl_premissas
"""
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import pandas as pd
from pydantic import ValidationError

from ..domain.schemas import (
    InstrutorSchema,
    DemandaSlotsSchema,
    SimuladorSchema,
    PremissasModel,
    CrewStaffingItem
)
from ..parsers.staffing_parser import CrewStaffingParser
from ..utils.date_utils import normalizar_ano_mes, normalizar_mes_ano


class DataLoaderError(Exception):
    """Exceção levantada para erros de leitura ou validação de schemas."""
    pass


class DataLoader:
    """Carregador central de dados brutos com sanitização e conversão de schemas."""

    @staticmethod
    def ler_tabela_arquivo(caminho: Union[str, Path]) -> pd.DataFrame:
        """
        Lê arquivos no formato .xlsx ou .csv com autodetecção de encoding e delimitador.
        """
        path = Path(caminho)
        if not path.exists():
            raise DataLoaderError(f"Arquivo não encontrado: {path.resolve()}")

        extensao = path.suffix.lower()

        if extensao == ".xlsx":
            try:
                df = pd.read_excel(path)
                df.columns = [str(c).strip() for c in df.columns]
                return df
            except Exception as e:
                raise DataLoaderError(f"Erro ao ler arquivo Excel '{path.name}': {e}")

        elif extensao == ".csv":
            delimitadores = [",", ";", "\t", "|"]
            encodings = ["utf-8-sig", "utf-8", "latin-1"]

            for enc in encodings:
                for sep in delimitadores:
                    try:
                        df = pd.read_csv(path, sep=sep, encoding=enc)
                        if len(df.columns) > 1:
                            df.columns = [str(c).strip() for c in df.columns]
                            return df
                    except Exception:
                        continue

            try:
                df = pd.read_csv(path)
                df.columns = [str(c).strip() for c in df.columns]
                return df
            except Exception as e:
                raise DataLoaderError(f"Erro ao ler CSV '{path.name}': {e}")
        else:
            raise DataLoaderError(f"Formato de arquivo não suportado: '{extensao}'. Esperado .csv ou .xlsx.")

    @classmethod
    def carregar_instrutores(cls, caminho: Union[str, Path]) -> List[InstrutorSchema]:
        """Carrega e valida a base de instrutores (tbl_instrutores)."""
        df = cls.ler_tabela_arquivo(caminho)

        mapeamento = {col: str(col).strip().lower().replace(" ", "_") for col in df.columns}
        df = df.rename(columns=mapeamento)

        colunas_obrigatorias = ["re", "nome", "frota", "funcao"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                raise DataLoaderError(f"tbl_instrutores: coluna obrigatória ausente '{col}'")

        registros: List[InstrutorSchema] = []
        erros: List[str] = []

        for idx, row in df.iterrows():
            linha_dict = row.to_dict()

            # Converte RE (numérico inteiro, float ou string) para string sanitizada
            re_val = linha_dict.get("re")
            if pd.isna(re_val) or re_val is None:
                re_str = ""
            elif isinstance(re_val, (int, float)):
                re_str = str(int(re_val)).strip()
            else:
                re_str = str(re_val).strip()
                if re_str.endswith(".0"):
                    re_str = re_str[:-2]
            linha_dict["re"] = re_str

            # Trata booleanos (True/False, 1/0, Sim/Não, S/N)
            for bool_col in ["avaliador", "examinador"]:
                val = linha_dict.get(bool_col, False)
                if pd.isna(val):
                    linha_dict[bool_col] = False
                elif isinstance(val, (int, float)):
                    linha_dict[bool_col] = bool(int(val))
                elif isinstance(val, str):
                    val_clean = val.strip().lower()
                    linha_dict[bool_col] = val_clean in ["true", "1", "sim", "s", "yes", "y", "x"]
                else:
                    linha_dict[bool_col] = bool(val)

            # Trata datas vazias (converte NaN/NaT/vazio para None)
            for date_col in ["data_inicio", "data_fim", "data_movimentacao"]:
                val = linha_dict.get(date_col)
                if pd.isna(val) or val is None or str(val).strip().lower() in ["nat", "none", "nan", "<na>", ""]:
                    linha_dict[date_col] = None
                else:
                    try:
                        linha_dict[date_col] = pd.to_datetime(val).date()
                    except Exception:
                        linha_dict[date_col] = None

            # Trata campos de texto opcionais (movimentacao_prevista)
            mov = linha_dict.get("movimentacao_prevista")
            if pd.isna(mov) or mov is None or str(mov).strip().lower() in ["none", "nan", "nat", "<na>", "null", ""]:
                linha_dict["movimentacao_prevista"] = None
            else:
                linha_dict["movimentacao_prevista"] = str(mov).strip()

            try:
                inst = InstrutorSchema(**linha_dict)
                registros.append(inst)
            except ValidationError as ve:
                erros.append(f"Linha {idx + 2} ({linha_dict.get('nome', 'N/D')}): {ve}")

        if erros:
            primeiros_erros = "\n".join(erros[:5])
            raise DataLoaderError(
                f"Foram encontrados {len(erros)} erros de validação na tbl_instrutores:\n{primeiros_erros}"
            )

        return registros

    @classmethod
    def carregar_simuladores(cls, caminho: Union[str, Path]) -> Dict[str, SimuladorSchema]:
        """Carrega e valida a base de dispositivos de simulador (tbl_simuladores)."""
        df = cls.ler_tabela_arquivo(caminho)

        mapeamento = {col: str(col).strip().lower().replace(" ", "_") for col in df.columns}
        df = df.rename(columns=mapeamento)

        colunas_obrigatorias = ["frota", "qtd_dispositivos", "slots_dia"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                raise DataLoaderError(f"tbl_simuladores: coluna obrigatória ausente '{col}'")

        simuladores: Dict[str, SimuladorSchema] = {}

        for _, row in df.iterrows():
            linha_dict = row.to_dict()
            try:
                sim = SimuladorSchema(
                    frota=str(linha_dict["frota"]).strip().upper(),
                    qtd_dispositivos=int(linha_dict["qtd_dispositivos"]),
                    slots_dia=int(linha_dict["slots_dia"])
                )
                simuladores[sim.frota] = sim
            except ValidationError as ve:
                raise DataLoaderError(f"Erro em tbl_simuladores para a frota {linha_dict.get('frota')}: {ve}")

        return simuladores

    @classmethod
    def carregar_demanda_slots(cls, caminho: Union[str, Path]) -> List[DemandaSlotsSchema]:
        """Carrega e valida a base de demanda mensal de slots (tbl_demanda_slots)."""
        df = cls.ler_tabela_arquivo(caminho)

        mapeamento = {col: str(col).strip().lower().replace(" ", "_") for col in df.columns}
        df = df.rename(columns=mapeamento)

        colunas_obrigatorias = ["frota", "mes", "demanda_slots"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                raise DataLoaderError(f"tbl_demanda_slots: coluna obrigatória ausente '{col}'")

        registros: List[DemandaSlotsSchema] = []
        erros: List[str] = []

        for idx, row in df.iterrows():
            frota = str(row["frota"]).strip()
            mes_raw = str(row["mes"]).strip()
            try:
                mes_norm = normalizar_ano_mes(mes_raw)
            except ValueError:
                erros.append(f"Linha {idx + 2}: Mês inválido '{mes_raw}'")
                continue

            try:
                slots = int(float(row["demanda_slots"]))
            except (ValueError, TypeError):
                erros.append(f"Linha {idx + 2}: Valor de demanda de slots inválido '{row['demanda_slots']}'")
                continue

            try:
                item = DemandaSlotsSchema(frota=frota, mes=mes_norm, demanda_slots=slots)
                registros.append(item)
            except ValidationError as ve:
                erros.append(f"Linha {idx + 2}: Erro de validação: {ve}")

        if erros:
            raise DataLoaderError(f"Erros na leitura de tbl_demanda_slots:\n" + "\n".join(erros[:10]))

        return registros

    @classmethod
    def carregar_premissas(cls, caminho: Union[str, Path]) -> PremissasModel:
        """Carrega a tbl_premissas com suporte a formato vertical ou horizontal."""
        df = cls.ler_tabela_arquivo(caminho)
        df_cols_lower = [str(c).strip().lower() for c in df.columns]

        dict_premissas: Dict[str, Any] = {}

        if any(c in ["premissa", "chave", "parametro", "param"] for c in df_cols_lower) and \
           any(c in ["valor", "val", "value"] for c in df_cols_lower):

            col_chave = next(c for c in df.columns if str(c).strip().lower() in ["premissa", "chave", "parametro", "param"])
            col_valor = next(c for c in df.columns if str(c).strip().lower() in ["valor", "val", "value"])

            for _, row in df.iterrows():
                chave = str(row[col_chave]).strip().upper()
                valor = row[col_valor]
                dict_premissas[chave] = valor

        else:
            primeira_linha = df.iloc[0].to_dict()
            for k, v in primeira_linha.items():
                dict_premissas[str(k).strip().upper()] = v

        kwargs = {}
        populacoes_frota: Dict[str, float] = {}

        for chave, val in dict_premissas.items():
            if pd.isna(val):
                continue
            chave_upper = chave.upper().strip()
            if chave_upper.startswith("POPULACAO_PERIODICOS_") and chave_upper != "POPULACAO_PERIODICOS_PADRAO":
                frota_nome = chave_upper.replace("POPULACAO_PERIODICOS_", "").strip()
                try:
                    populacoes_frota[frota_nome] = float(val)
                except Exception:
                    pass
            elif chave_upper.startswith("POPULACAO_") and not chave_upper.startswith("POPULACAO_PERIODICOS") and chave_upper != "POPULACAO_PADRAO":
                frota_nome = chave_upper.replace("POPULACAO_", "").strip()
                try:
                    populacoes_frota[frota_nome] = float(val)
                except Exception:
                    pass

        for campo, field_info in PremissasModel.model_fields.items():
            if campo == "POPULACOES_FROTA":
                kwargs[campo] = populacoes_frota
                continue
            if campo in dict_premissas:
                val = dict_premissas[campo]
                if pd.isna(val):
                    continue
                tipo = field_info.annotation
                try:
                    if tipo == int:
                        kwargs[campo] = int(float(val))
                    elif tipo == float:
                        kwargs[campo] = float(val)
                    else:
                        kwargs[campo] = str(val).strip()
                except Exception as e:
                    raise DataLoaderError(f"Valor inválido para a premissa '{campo}': '{val}'. Erro: {e}")

        try:
            return PremissasModel(**kwargs)
        except ValidationError as ve:
            raise DataLoaderError(f"Erro de validação nas premissas: {ve}")

    @classmethod
    def carregar_crew_staffing(
        cls,
        caminho: Union[str, Path],
        premissas: PremissasModel
    ) -> List[CrewStaffingItem]:
        """Carrega e realiza o parsing especializado do Crew Staffing."""
        df = cls.ler_tabela_arquivo(caminho)
        parser = CrewStaffingParser()
        return parser.parse_dataframe(df, premissas)