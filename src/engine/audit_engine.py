"""
Motor de Auditoria Analítica e Rastreabilidade do SIPCAP.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
from ..domain.schemas import CalculoMensalFrota, PremissasModel


class AuditEngine:
    @classmethod
    def gerar_dataframe_auditoria(
        cls,
        calculos: List[CalculoMensalFrota]
    ) -> pd.DataFrame:
        registros = []
        for c in calculos:
            registros.append({
                "Frota": c.frota,
                "Mês": c.mes_exibicao,
                "Ano_Mes": c.ano_mes,
                "Dias": c.dias_mes,
                "Qtd_Simuladores": c.qtd_dispositivos,
                "Slots_Dia": c.slots_dia,
                "Capacidade_Simulador": c.capacidade_simulador,
                "Demanda_Real": c.demanda_real,
                "Demanda_Considerada": c.demanda_considerada,
                "Motivo_Demanda": c.motivo_demanda_considerada,
                "Periodicos_Mes": c.periodicos_mes,
                "Cheques_ANAC_Periodicos": c.cheques_anac_periodicos,
                "Cheques_CIA_Periodicos": c.cheques_cia_periodicos,
                "Cheques_ANAC_Movimentacao": c.cheques_anac_movimentacao,
                "Cheques_ANAC_Transferencias": c.cheques_anac_transferencias,
                "Cheques_ANAC_Upgrade": c.cheques_anac_upgrade,
                "Cheques_ANAC_New_Hiring": c.cheques_anac_new_hiring,
                "Total_Cheques_Staffing": c.total_cheques_anac_staffing,
                "Cheques_ANAC_Base": c.cheques_anac_base,
                "Buffer_Cheques_ANAC": c.buffer_cheques_valor,
                "Demanda_EX_Total": c.demanda_ex_total,
                "Demanda_EX_Aeronauta": c.demanda_ex_aeronauta,
                "Demanda_EX_Aeroviario": c.demanda_ex_aeroviario,
                "Demanda_AVA_Total": c.demanda_ava_total,
                "Demanda_AVA_Aeronauta": c.demanda_ava_aeronauta,
                "Demanda_AVA_Aeroviario": c.demanda_ava_aeroviario,
                "HC_Bruto_EX_Aeronauta": c.hc_bruto_ex_aeronauta,
                "HC_Bruto_EX_Aeroviario": c.hc_bruto_ex_aeroviario,
                "HC_Bruto_AVA_Aeronauta": c.hc_bruto_ava_aeronauta,
                "HC_Bruto_AVA_Aeroviario": c.hc_bruto_ava_aeroviario,
                "Indisp_Ferias_EX_Aero": c.indisp_ferias_ex_aero,
                "Indisp_Ferias_EX_Viario": c.indisp_ferias_ex_viario,
                "Indisp_Ferias_AVA_Aero": c.indisp_ferias_ava_aero,
                "Indisp_Ferias_AVA_Viario": c.indisp_ferias_ava_viario,
                "Indisp_Trein_EX_Aero": c.indisp_trein_ex_aero,
                "Indisp_Trein_EX_Viario": c.indisp_trein_ex_viario,
                "Indisp_Trein_AVA_Aero": c.indisp_trein_ava_aero,
                "Indisp_Trein_AVA_Viario": c.indisp_trein_ava_viario,
                "PSM_AVA_Viario": c.psm_ava_viario,
                "Necessidade_EX_Aeronauta": c.nec_ex_aeronauta,
                "Necessidade_EX_Aeroviario": c.nec_ex_aeroviario,
                "Necessidade_AVA_Aeronauta": c.nec_ava_aeronauta,
                "Necessidade_AVA_Aeroviario": c.nec_ava_aeroviario,
                "Disponivel_EX_Aeronauta": c.disp_ex_aeronauta,
                "Disponivel_EX_Aeroviario": c.disp_ex_aeroviario,
                "Disponivel_AVA_Aeronauta": c.disp_ava_aeronauta,
                "Disponivel_AVA_Aeroviario": c.disp_ava_aeroviario,
                "Saldo_EX_Aeronauta": c.saldo_ex_aeronauta,
                "Saldo_EX_Aeroviario": c.saldo_ex_aeroviario,
                "Saldo_AVA_Aeronauta": c.saldo_ava_aeronauta,
                "Saldo_AVA_Aeroviario": c.saldo_ava_aeroviario,
                "RAG_EX_Aeronauta": c.status_rag_ex_aero,
                "RAG_EX_Aeroviario": c.status_rag_ex_viario,
                "RAG_AVA_Aeronauta": c.status_rag_ava_aero,
                "RAG_AVA_Aeroviario": c.status_rag_ava_viario,
                "RAG_Frota": c.status_rag_frota,
            })
        return pd.DataFrame(registros)

    @classmethod
    def formatar_memoria_calculo_markdown(
        cls,
        c: CalculoMensalFrota,
        premissas: PremissasModel
    ) -> str:
        texto = f"""
### Memória de Cálculo Analítico - Frota {c.frota} ({c.mes_exibicao})

#### 1. Capacidade Física dos Simuladores (RN-01)
- **Fórmula**: `Dias_Mes ({c.dias_mes}) × Slots_Dia ({c.slots_dia}) × Qtd_Dispositivos ({c.qtd_dispositivos})`
- **Capacidade Calculada**: **`{c.capacidade_simulador}` slots**

#### 2. Demanda Considerada (RN-02)
- **Demanda Real Informada**: `{c.demanda_real}` slots
- **Capacidade Simulador**: `{c.capacidade_simulador}` slots
- **Fórmula**: `MAX(Demanda Real, Capacidade Simulador)`
- **Demanda Considerada**: **`{c.demanda_considerada}` slots**
- **Justificativa**: {c.motivo_demanda_considerada}

#### 3. Cheques Periódicos (RN-03 e RN-04)
- **Volume Mensal de Periódicos**: `{c.periodicos_mes:.2f}` tripulantes
- **Duplas Formadas**: `{c.periodicos_mes / 2.0:.2f}` duplas
- **Cheques ANAC Periódicos** (Examinadores): **`{c.cheques_anac_periodicos:.2f}`**
- **Cheques CIA Periódicos** (Avaliadores): **`{c.cheques_cia_periodicos:.2f}`**

#### 4. Cheques de Crew Staffing Segregados (RN-05 e RN-06)
- **Cheques ANAC de Movimentação (Total Coluna Frota)**: **`{c.cheques_anac_movimentacao}`**
  * Transferências Inter-frotas: `{c.cheques_anac_transferencias}`
  * Upgrades na mesma Frota: `{c.cheques_anac_upgrade}`
  * Contratações New Hiring: `{c.cheques_anac_new_hiring}`
- **Total Cheques ANAC Staffing**: **`{c.total_cheques_anac_staffing}`** (com offset de {premissas.OFFSET_CHEQUE_MOVIMENTACAO} meses)

#### 5. Demanda dos Examinadores (RN-07)
- **Cheques ANAC Base**: `{c.cheques_anac_periodicos:.2f} + {c.total_cheques_anac_staffing} = {c.cheques_anac_base:.2f}`
- **Buffer de Segurança ({premissas.BUFFER_CHEQUES}%)**: `{c.buffer_cheques_valor:.2f}`
- **Demanda Total de Examinadores**: **`{c.demanda_ex_total:.2f}` slots**
  * Split Aeronauta ({premissas.PERC_EX_AERONAUTA}%): **`{c.demanda_ex_aeronauta:.2f}` slots**
  * Split Aeroviário ({premissas.PERC_EX_AEROVIARIO}%): **`{c.demanda_ex_aeroviario:.2f}` slots**

#### 6. Demanda dos Avaliadores (RN-08)
- **Demanda Total de Avaliadores**: **`{c.demanda_ava_total:.2f}` slots**
  * Split Aeroviário ({premissas.PERC_AVA_AEROVIARIO}%): **`{c.demanda_ava_aeroviario:.2f}` slots**
  * Split Aeronauta ({premissas.PERC_AVA_AERONAUTA}%): **`{c.demanda_ava_aeronauta:.2f}` slots**

#### 7. Conversão em Headcount e Indisponibilidade (RN-09, RN-10, RN-11)
- **Examinador Aeronauta**:
  * HC Bruto: `{c.demanda_ex_aeronauta:.2f} / {premissas.SESSAO_EX_AERONAUTA} = {c.hc_bruto_ex_aeronauta:.2f}`
  * Indisponibilidade Férias ({premissas.FATOR_FERIAS_PERC}%): `{c.indisp_ferias_ex_aero:.2f}`
  * Indisponibilidade Treinamento ({premissas.FATOR_TREINAMENTO_PERC}%): `{c.indisp_trein_ex_aero:.2f}`
  * **Necessidade Final**: **`{c.nec_ex_aeronauta:.2f}`**
- **Examinador Aeroviário**:
  * HC Bruto: `{c.demanda_ex_aeroviario:.2f} / {premissas.SESSAO_EX_AEROVIARIO} = {c.hc_bruto_ex_aeroviario:.2f}`
  * Indisponibilidade Férias ({premissas.FATOR_FERIAS_PERC}%): `{c.indisp_ferias_ex_viario:.2f}`
  * Indisponibilidade Treinamento ({premissas.FATOR_TREINAMENTO_PERC}%): `{c.indisp_trein_ex_viario:.2f}`
  * **Necessidade Final**: **`{c.nec_ex_aeroviario:.2f}`**
- **Avaliador Aeronauta**:
  * HC Bruto: `{c.demanda_ava_aeronauta:.2f} / {premissas.SESSAO_AVA_AERONAUTA} = {c.hc_bruto_ava_aeronauta:.2f}`
  * Indisponibilidade Férias ({premissas.FATOR_FERIAS_PERC}%): `{c.indisp_ferias_ava_aero:.2f}`
  * Indisponibilidade Treinamento ({premissas.FATOR_TREINAMENTO_PERC}%): `{c.indisp_trein_ava_aero:.2f}`
  * **Necessidade Final**: **`{c.nec_ava_aeronauta:.2f}`**
- **Avaliador Aeroviário**:
  * HC Bruto: `{c.demanda_ava_aeroviario:.2f} / {premissas.SESSAO_AVA_AEROVIARIO} = {c.hc_bruto_ava_aeroviario:.2f}`
  * Indisponibilidade Férias ({premissas.FATOR_FERIAS_PERC}%): `{c.indisp_ferias_ava_viario:.2f}`
  * Indisponibilidade Treinamento ({premissas.FATOR_TREINAMENTO_PERC}%): `{c.indisp_trein_ava_viario:.2f}`
  * Cobertura PSM (RN-11): **`+{c.psm_ava_viario:.2f}`**
  * **Necessidade Final**: **`{c.nec_ava_aeroviario:.2f}`**

#### 8. Balanço de Disponibilidade e Saldo
| Função | Necessidade | Disponível | Saldo Líquido | Status RAG |
| :--- | :---: | :---: | :---: | :---: |
| **Examinador Aeronauta** | {c.nec_ex_aeronauta:.2f} | {c.disp_ex_aeronauta} | **{c.saldo_ex_aeronauta:+.2f}** | `{c.status_rag_ex_aero}` |
| **Examinador Aeroviário** | {c.nec_ex_aeroviario:.2f} | {c.disp_ex_aeroviario} | **{c.saldo_ex_aeroviario:+.2f}** | `{c.status_rag_ex_viario}` |
| **Avaliador Aeronauta** | {c.nec_ava_aeronauta:.2f} | {c.disp_ava_aeronauta} | **{c.saldo_ava_aeronauta:+.2f}** | `{c.status_rag_ava_aero}` |
| **Avaliador Aeroviário** | {c.nec_ava_aeroviario:.2f} | {c.disp_ava_aeroviario} | **{c.saldo_ava_aeroviario:+.2f}** | `{c.status_rag_ava_viario}` |
| **Status Consolidado Frota** | - | - | - | **`{c.status_rag_frota}`** |
"""
        return texto.strip()