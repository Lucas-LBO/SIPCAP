"""
Schemas Pydantic para Validação dos Arquivos de Entrada e Dados de Domínio do SIPCAP.
"""
from datetime import date, datetime
from typing import Optional, List, Any, Dict
import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator
from .enums import FrotaEnum, CategoriaFuncaoEnum, TipoStaffingEnum


class InstrutorSchema(BaseModel):
    re: str = Field(..., description="Registro de Empregado / Matrícula")
    nome: str = Field(..., description="Nome completo do instrutor")
    frota: str = Field(..., description="Frota atual (ex.: ERJ, A320, ATR, A330)")
    funcao: str = Field(..., description="Aeronauta ou Aeroviario")
    avaliador: bool = Field(default=False, description="Possui habilitação de Avaliador")
    examinador: bool = Field(default=False, description="Possui credenciamento de Examinador ANAC")
    data_inicio: Optional[date] = Field(default=None, description="Data de início da função")
    data_fim: Optional[date] = Field(default=None, description="Data prevista de término/devolução")
    movimentacao_prevista: Optional[str] = Field(default=None, description="Ex: Promocao_Examinador, Transferencia")
    data_movimentacao: Optional[date] = Field(default=None, description="Data prevista da movimentação")

    @field_validator("re", mode="before")
    @classmethod
    def validar_re(cls, v: Any) -> str:
        if v is None or (isinstance(v, float) and (v != v)):
            raise ValueError("RE não pode ser nulo.")
        if isinstance(v, (int, float)):
            return str(int(v)).strip()
        v_str = str(v).strip()
        if v_str.endswith(".0"):
            v_str = v_str[:-2]
        if not v_str:
            raise ValueError("RE não pode ser vazio.")
        return v_str

    @field_validator("movimentacao_prevista", mode="before")
    @classmethod
    def validar_movimentacao_prevista(cls, v: Any) -> Optional[str]:
        if v is None or pd.isna(v):
            return None
        v_str = str(v).strip()
        if not v_str or v_str.lower() in ["nan", "none", "nat", "<na>", "null"]:
            return None
        return v_str

    @field_validator("data_inicio", "data_fim", "data_movimentacao", mode="before")
    @classmethod
    def validar_datas_opcionais(cls, v: Any) -> Optional[date]:
        if v is None or pd.isna(v):
            return None
        if isinstance(v, (date, datetime, pd.Timestamp)):
            return v.date() if isinstance(v, (datetime, pd.Timestamp)) else v
        v_str = str(v).strip()
        if not v_str or v_str.lower() in ["nat", "none", "nan", "<na>", "null"]:
            return None
        try:
            return pd.to_datetime(v).date()
        except Exception:
            return None

    @field_validator("frota")
    @classmethod
    def validar_frota(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("funcao")
    @classmethod
    def validar_funcao(cls, v: str) -> str:
        v_clean = v.strip().capitalize().replace("á", "a").replace("Á", "A")
        if v_clean not in ["Aeronauta", "Aeroviario"]:
            raise ValueError(f"Função deve ser 'Aeronauta' ou 'Aeroviario'. Recebido: {v}")
        return v_clean

    @model_validator(mode="after")
    def validar_pre_requisito_examinador(self):
        if self.examinador and not self.avaliador:
            self.avaliador = True
        return self


class DemandaSlotsSchema(BaseModel):
    frota: str = Field(..., description="Frota (ex: ERJ, A320)")
    mes: str = Field(..., description="Mês de referência (ex: jan/27 ou 2027-01)")
    demanda_slots: int = Field(..., ge=0, description="Quantidade de slots demandados")

    @field_validator("frota")
    @classmethod
    def validar_frota(cls, v: str) -> str:
        return v.strip().upper()


class SimuladorSchema(BaseModel):
    frota: str = Field(..., description="Frota correspondente")
    qtd_dispositivos: int = Field(..., gt=0, description="Quantidade de dispositivos FFS")
    slots_dia: int = Field(..., gt=0, description="Slots disponíveis por dia por dispositivo")

    @field_validator("frota")
    @classmethod
    def validar_frota(cls, v: str) -> str:
        return v.strip().upper()


class PremissasModel(BaseModel):
    SESSAO_AVA_AERONAUTA: int = Field(default=7, gt=0, description="Slots/mês por Avaliador Aeronauta")
    SESSAO_AVA_AEROVIARIO: int = Field(default=14, gt=0, description="Slots/mês por Avaliador Aeroviário")
    SESSAO_EX_AERONAUTA: int = Field(default=7, gt=0, description="Slots/mês por Examinador Aeronauta")
    SESSAO_EX_AEROVIARIO: int = Field(default=14, gt=0, description="Slots/mês por Examinador Aeroviário")
    BUFFER_CHEQUES: float = Field(default=20.0, ge=0.0, description="% de buffer sobre cheques ANAC")
    PERC_EX_AERONAUTA: float = Field(default=70.0, ge=0.0, le=100.0, description="% cheques ANAC para Aeronauta")
    PERC_EX_AEROVIARIO: float = Field(default=30.0, ge=0.0, le=100.0, description="% cheques ANAC para Aeroviário")
    PERC_AVA_AEROVIARIO: float = Field(default=70.0, ge=0.0, le=100.0, description="% sessões Avaliador Aeroviário")
    PERC_AVA_AERONAUTA: float = Field(default=30.0, ge=0.0, le=100.0, description="% sessões Avaliador Aeronauta")
    PRAZO_FORMACAO_AVALIADOR: int = Field(default=3, gt=0, description="Meses de formação para novo Avaliador")
    OFFSET_CHEQUE_MOVIMENTACAO: int = Field(default=2, ge=0, description="Meses de carência para o cheque")
    PSM_AEROVIARIO: int = Field(default=2, ge=0, description="Headcount adicional para suporte PSM")
    MESES_ALTA: str = Field(default="JAN,JUL,DEZ", description="Meses de alta temporada de voo")
    PERC_ALTA: float = Field(default=60.0, ge=0.0, le=100.0, description="% da média mensal na alta temporada")
    FATOR_FERIAS_PERC: float = Field(default=8.33, ge=0.0, description="% indisponibilidade de férias (1/12 ~ 8.33%)")
    FATOR_TREINAMENTO_PERC: float = Field(default=4.0, ge=0.0, description="% indisponibilidade de treinamentos (13 dias/ano ~ 4%)")
    POPULACAO_PERIODICOS_PADRAO: int = Field(default=840, ge=0, description="População anual base para periódicos")
    POPULACOES_FROTA: Dict[str, float] = Field(default_factory=dict, description="População específica por frota")
    CHEQUES_POR_TRIPULANTE_STAFFING: int = Field(default=1, ge=1, description="Cheques ANAC por tripulante (padrão = 1)")
    CAPACIDADE_RATIO_AEROVIARIO: float = Field(default=2.0, gt=0, description="Equivalência RN-12: 1 Aeroviário = 2 Aeronautas")

    def obter_populacao_frota(self, frota: str) -> float:
        frota_clean = frota.strip().upper()
        if frota_clean in self.POPULACOES_FROTA:
            return float(self.POPULACOES_FROTA[frota_clean])
        return float(self.POPULACAO_PERIODICOS_PADRAO)

    @model_validator(mode="after")
    def validar_splits(self):
        soma_ex = round(self.PERC_EX_AERONAUTA + self.PERC_EX_AEROVIARIO, 2)
        if soma_ex != 100.0:
            raise ValueError(f"Soma de PERC_EX deve ser 100.0. Atual: {soma_ex}")
        soma_ava = round(self.PERC_AVA_AEROVIARIO + self.PERC_AVA_AERONAUTA, 2)
        if soma_ava != 100.0:
            raise ValueError(f"Soma de PERC_AVA deve ser 100.0. Atual: {soma_ava}")
        return self


class CrewStaffingItem(BaseModel):
    career_move_original: Optional[str] = Field(default="", description="Descrição original")
    tipo_evento: TipoStaffingEnum = Field(..., description="Movimentacao, Upgrade ou New Hiring")
    frota_origem: Optional[str] = Field(default=None, description="Frota de origem")
    frota_destino: str = Field(..., description="Frota de destino")
    ano_mes_entrada: str = Field(default="", description="Mês de entrada (YYYY-MM)")
    qtd_tripulantes: int = Field(..., ge=1, description="Quantidade de tripulantes")
    offset_meses: int = Field(default=2, ge=0, description="Offset de carência até o cheque")
    ano_mes_cheque: str = Field(..., description="Mês do cheque")
    cheques_gerados: int = Field(..., ge=0, description="Cheques gerados pelo evento")
    funcao: str = Field(default="Piloto", description="Função operacional")
    mes_origem: Optional[str] = Field(default=None, description="Alias para ano_mes_entrada")

    @model_validator(mode="before")
    @classmethod
    def sincronizar_campos_tempo_e_funcao(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "mes_origem" in data and data["mes_origem"] and not data.get("ano_mes_entrada"):
                data["ano_mes_entrada"] = data["mes_origem"]
            elif "ano_mes_entrada" in data and data["ano_mes_entrada"] and not data.get("mes_origem"):
                data["mes_origem"] = data["ano_mes_entrada"]
            if not data.get("funcao"):
                cm = str(data.get("career_move_original", "")).upper()
                if "CA" in cm:
                    data["funcao"] = "Comandante"
                elif "FO" in cm:
                    data["funcao"] = "Copiloto"
                else:
                    data["funcao"] = "Piloto"
        return data


class CalculoMensalFrota(BaseModel):
    frota: str
    ano_mes: str
    mes_exibicao: str
    dias_mes: int
    qtd_dispositivos: int
    slots_dia: int
    capacidade_simulador: int
    demanda_real: int
    demanda_considerada: int
    motivo_demanda_considerada: str
    periodicos_mes: float
    cheques_anac_periodicos: float
    cheques_cia_periodicos: float
    cheques_anac_movimentacao: int
    cheques_anac_transferencias: int = 0
    cheques_anac_upgrade: int
    cheques_anac_new_hiring: int
    total_cheques_anac_staffing: int
    cheques_anac_base: float
    buffer_cheques_valor: float
    demanda_ex_total: float
    demanda_ex_aeronauta: float
    demanda_ex_aeroviario: float
    demanda_ava_total: float
    demanda_ava_aeroviario: float
    demanda_ava_aeronauta: float
    hc_bruto_ex_aeronauta: float
    hc_bruto_ex_aeroviario: float
    hc_bruto_ava_aeronauta: float
    hc_bruto_ava_aeroviario: float
    indisp_ferias_ex_aero: float
    indisp_ferias_ex_viario: float
    indisp_ferias_ava_aero: float
    indisp_ferias_ava_viario: float
    indisp_trein_ex_aero: float
    indisp_trein_ex_viario: float
    indisp_trein_ava_aero: float
    indisp_trein_ava_viario: float
    psm_ava_viario: float
    nec_ex_aeronauta: float
    nec_ex_aeroviario: float
    nec_ava_aeronauta: float
    nec_ava_aeroviario: float
    disp_ex_aeronauta: int
    disp_ex_aeroviario: int
    disp_ava_aeronauta: int
    disp_ava_aeroviario: int
    saldo_ex_aeronauta: float
    saldo_ex_aeroviario: float
    saldo_ava_aeronauta: float
    saldo_ava_aeroviario: float
    status_rag_ex_aero: str
    status_rag_ex_viario: str
    status_rag_ava_aero: str
    status_rag_ava_viario: str
    status_rag_frota: str


class RecomendacaoPrescritiva(BaseModel):
    frota: str
    ano_mes_evento: str
    mes_exibicao: str
    funcao: str
    deficit_original: float
    cobertura_cruzada: bool
    deficit_remanescente: float
    prioridade: str
    acao_recomendada: str
    mes_limite_inicio: str
    mes_limite_exibicao: str
    antecedencia_meses: int


class NecessidadeEstrategica13M(BaseModel):
    frota: str
    funcao: str
    mes_referencia: str
    mes_referencia_exibicao: str
    horizonte_analisado: str
    total_meses: int
    deficit_pico: float
    deficit_medio: float
    deficit_mediano: float
    meses_criticos_count: int
    meses_criticos_lista: str
    formacao_estrategica_sugerida: int
    formacao_pico_sugerida: int
    estrategia_sugerida: str


class NecessidadeEstrategicaConsolidada(BaseModel):
    frota: str
    funcao: str
    periodo_analisado: str
    total_meses: int
    deficit_pico: float
    deficit_medio: float
    deficit_mediano: float
    meses_criticos_count: int
    cobertura_cruzada_media: float
    deficit_liquido_estrategico: float
    formacao_estrategica_sugerida: int
    diagnostico_estrategico: str


class CoberturaCruzadaRN12(BaseModel):
    frota: str
    ano_mes: str
    mes_exibicao: str
    funcao_deficitaria: str
    funcao_superavitaria: str
    deficit_original: float
    superavit_disponivel: float
    capacidade_cobertura: float
    percentual_cobertura: float
    tipo_cobertura: str
    deficit_remanescente: float
    mensagem_diagnostico: str


class CoberturaCruzadaConsolidada(BaseModel):
    frota: str
    funcao: str
    periodo_analisado: str
    deficit_medio: float
    capacidade_media_cobertura: float
    deficit_liquido_estrategico: float
    percentual_cobertura_media: float
    diagnostico: str


# =====================================================================
# ALIASES DE COMPATIBILIDADE RETROATIVA
# =====================================================================
CoberturaCruzadaResultado = CoberturaCruzadaRN12
RecomendacaoAcao = RecomendacaoPrescritiva