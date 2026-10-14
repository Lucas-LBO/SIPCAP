"""
Orquestrador Central do Pipeline Analítico do SIPCAP.
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union, Any
import pandas as pd

from ..domain.schemas import (
    PremissasModel,
    SimuladorSchema,
    DemandaSlotsSchema,
    CrewStaffingItem,
    InstrutorSchema,
    CalculoMensalFrota,
    CoberturaCruzadaResultado,
    RecomendacaoAcao
)
from ..loaders.data_loader import DataLoader
from .capacity_engine import CapacityEngine
from .recommendation_engine import RecommendationEngine
from .audit_engine import AuditEngine


class SIPCAPOrchestrator:
    def __init__(
        self,
        premissas: PremissasModel,
        simuladores: Dict[str, SimuladorSchema],
        demanda_slots: List[DemandaSlotsSchema],
        staffing_itens: List[CrewStaffingItem],
        instrutores: List[InstrutorSchema]
    ):
        self.premissas = premissas
        self.simuladores = simuladores
        self.demanda_slots = sorted(demanda_slots, key=lambda x: (x.frota, x.mes))
        self.staffing_itens = staffing_itens
        self.instrutores = instrutores

        self.calculos: List[CalculoMensalFrota] = []
        self.coberturas_cruzadas: List[CoberturaCruzadaResultado] = []
        self.recomendacoes: List[RecomendacaoAcao] = []
        self.necessidades_estrategicas_consolidadas: List[Any] = []
        self.coberturas_cruzadas_consolidadas: List[Any] = []
        self._df_auditoria: Optional[pd.DataFrame] = None

    @classmethod
    def carregar_de_arquivos(
        cls,
        caminho_premissas: Union[str, Path],
        caminho_simuladores: Union[str, Path],
        caminho_demanda_slots: Union[str, Path],
        caminho_crew_staffing: Union[str, Path],
        caminho_instrutores: Union[str, Path]
    ) -> "SIPCAPOrchestrator":
        premissas = DataLoader.carregar_premissas(caminho_premissas)
        simuladores = DataLoader.carregar_simuladores(caminho_simuladores)
        demanda_slots = DataLoader.carregar_demanda_slots(caminho_demanda_slots)
        staffing_itens = DataLoader.carregar_crew_staffing(caminho_crew_staffing, premissas)
        instrutores = DataLoader.carregar_instrutores(caminho_instrutores)

        return cls(
            premissas=premissas,
            simuladores=simuladores,
            demanda_slots=demanda_slots,
            staffing_itens=staffing_itens,
            instrutores=instrutores
        )

    def executar(self) -> "SIPCAPOrchestrator":
        self.calculos.clear()
        self.coberturas_cruzadas.clear()
        self.recomendacoes.clear()

        frotas_presentes = sorted(list({d.frota for d in self.demanda_slots}))
        distribuicao_periodicos: Dict[Tuple[str, int], Dict[str, float]] = {}

        for frota in frotas_presentes:
            demandas_frota = [d for d in self.demanda_slots if d.frota == frota]
            anos_frota = {int(d.mes.split("-")[0]) for d in demandas_frota}

            for ano in anos_frota:
                pop_anual = self.premissas.obter_populacao_frota(frota)
                dist_ano = CapacityEngine.distribuir_treinamentos_periodicos(
                    ano=ano,
                    populacao_anual=pop_anual,
                    premissas=self.premissas
                )
                distribuicao_periodicos[(frota, ano)] = dist_ano

        for d in self.demanda_slots:
            frota = d.frota
            ano_mes = d.mes
            ano = int(ano_mes.split("-")[0])

            simulador = self.simuladores.get(frota)
            if not simulador:
                simulador = SimuladorSchema(frota=frota, qtd_dispositivos=1, slots_dia=5)

            dist_map = distribuicao_periodicos.get((frota, ano), {})
            periodicos_mes = dist_map.get(ano_mes, self.premissas.obter_populacao_frota(frota) / 12.0)

            calc = CapacityEngine.processar_mes_frota(
                frota=frota,
                ano_mes=ano_mes,
                simulador=simulador,
                demanda_real=d.demanda_slots,
                periodicos_mes=periodicos_mes,
                staffing_itens=self.staffing_itens,
                instrutores=self.instrutores,
                premissas=self.premissas
            )
            self.calculos.append(calc)

            cobs, recs = RecommendationEngine.gerar_recomendacoes_calculo(calc, self.premissas)
            self.coberturas_cruzadas.extend(cobs)
            self.recomendacoes.extend(recs)

        self._df_auditoria = AuditEngine.gerar_dataframe_auditoria(self.calculos)

        # Análise estratégica consolidada (Recomendação única por Frota e Função)
        (
            self.necessidades_estrategicas_consolidadas,
            self.coberturas_cruzadas_consolidadas
        ) = RecommendationEngine.calcular_necessidade_estrategica_consolidada(
            self.calculos, self.premissas
        )
        return self

    @property
    def dataframe_auditoria(self) -> pd.DataFrame:
        if self._df_auditoria is None:
            self.executar()
        return self._df_auditoria

    def obter_status_executivo_frotas(self) -> pd.DataFrame:
        if not self.calculos:
            self.executar()

        df = self.dataframe_auditoria
        resumo = []
        for frota, grupo in df.groupby("Frota"):
            status_pior = "Verde"
            if "Vermelho" in grupo["RAG_Frota"].values:
                status_pior = "Vermelho"
            elif "Amarelo" in grupo["RAG_Frota"].values:
                status_pior = "Amarelo"

            meses_criticos = grupo[grupo["RAG_Frota"] == "Vermelho"]["Mês"].tolist()
            menor_saldo = min(
                grupo["Saldo_EX_Aeronauta"].min(),
                grupo["Saldo_EX_Aeroviario"].min(),
                grupo["Saldo_AVA_Aeronauta"].min(),
                grupo["Saldo_AVA_Aeroviario"].min()
            )

            resumo.append({
                "Frota": frota,
                "Status": status_pior,
                "Menor_Saldo": round(menor_saldo, 2),
                "Meses_Criticos": ", ".join(meses_criticos) if meses_criticos else "Nenhum",
                "Total_Meses_Projetados": len(grupo)
            })

        return pd.DataFrame(resumo)