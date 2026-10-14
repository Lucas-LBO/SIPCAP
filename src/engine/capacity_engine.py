"""
Motor Analítico de Capacidade (Capacity Engine) do SIPCAP.
"""
from datetime import date
import calendar
from typing import List, Dict, Tuple, Optional
from ..domain.schemas import (
    CalculoMensalFrota,
    SimuladorSchema,
    PremissasModel,
    CrewStaffingItem,
    InstrutorSchema
)
from ..domain.enums import TipoStaffingEnum
from ..utils.date_utils import formatar_ano_mes_exibicao, normalizar_ano_mes


class CapacityEngine:
    @staticmethod
    def calcular_capacidade_simulador(
        qtd_dispositivos: int,
        slots_dia: int,
        ano_mes: str
    ) -> Tuple[int, int]:
        ano_mes_norm = normalizar_ano_mes(ano_mes)
        ano, mes = map(int, ano_mes_norm.split("-"))
        _, dias_mes = calendar.monthrange(ano, mes)
        capacidade_slots = dias_mes * slots_dia * qtd_dispositivos
        return capacidade_slots, dias_mes

    @staticmethod
    def calcular_demanda_considerada(
        demanda_real: int,
        capacidade_simulador: int
    ) -> Tuple[int, str]:
        if demanda_real >= capacidade_simulador:
            return demanda_real, f"Demanda real ({demanda_real}) >= Capacidade física ({capacidade_simulador})"
        else:
            return capacidade_simulador, f"Gargalo físico ativado: Capacidade simulador ({capacidade_simulador}) > Demanda real ({demanda_real})"

    @staticmethod
    def distribuir_treinamentos_periodicos(
        ano: int,
        populacao_anual: float,
        premissas: PremissasModel
    ) -> Dict[str, float]:
        meses_alta_nomes = [m.strip().upper() for m in premissas.MESES_ALTA.split(",") if m.strip()]
        mapa_meses = {
            "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
            "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
        }
        meses_alta_nums = [mapa_meses[m] for m in meses_alta_nomes if m in mapa_meses]

        media_mensal = populacao_anual / 12.0
        qtd_meses_alta = len(meses_alta_nums)
        qtd_meses_baixa = 12 - qtd_meses_alta

        valor_alta = media_mensal * (premissas.PERC_ALTA / 100.0)
        total_alta = valor_alta * qtd_meses_alta
        saldo_baixa = max(0.0, populacao_anual - total_alta)
        valor_baixa = saldo_baixa / max(1, qtd_meses_baixa)

        resultado = {}
        for m in range(1, 13):
            chave = f"{ano:04d}-{m:02d}"
            if m in meses_alta_nums:
                resultado[chave] = valor_alta
            else:
                resultado[chave] = valor_baixa
        return resultado

    @staticmethod
    def calcular_cheques_periodicos(periodicos_mes: float) -> Tuple[float, float]:
        duplas = periodicos_mes / 2.0
        cheques_anac = duplas * 2.0
        cheques_cia = duplas * 2.0
        return cheques_anac, cheques_cia

    @staticmethod
    def segregar_cheques_staffing(
        staffing_itens: List[CrewStaffingItem],
        frota: str,
        ano_mes: str
    ) -> Dict[str, int]:
        """
        RN-05 e RN-06: Cheques originados de Crew Staffing no mês do cheque.
        - total_movimentacao: soma de toda a coluna de movimentação da frota (transferências, upgrades e new hiring)
        - transferencias: transferências inter-frotas
        - upgrade: upgrades na mesma frota
        - new_hiring: contratações new hiring
        - total: total consolidado de cheques de staffing
        """
        transf = 0
        upg = 0
        nh = 0
        total = 0

        ano_mes_norm = normalizar_ano_mes(ano_mes)

        for item in staffing_itens:
            if item.frota_destino == frota and item.ano_mes_cheque == ano_mes_norm:
                total += item.cheques_gerados
                if item.tipo_evento == TipoStaffingEnum.MOVIMENTACAO:
                    transf += item.cheques_gerados
                elif item.tipo_evento == TipoStaffingEnum.UPGRADE:
                    upg += item.cheques_gerados
                elif item.tipo_evento == TipoStaffingEnum.NEW_HIRING:
                    nh += item.cheques_gerados

        return {
            "total_movimentacao": total,
            "movimentacao": transf,
            "transferencias": transf,
            "upgrade": upg,
            "new_hiring": nh,
            "total": total
        }

    @staticmethod
    def calcular_demanda_examinadores(
        cheques_anac_periodicos: float,
        total_cheques_anac_staffing: int,
        premissas: PremissasModel
    ) -> Tuple[float, float, float, float, float]:
        cheques_base = cheques_anac_periodicos + float(total_cheques_anac_staffing)
        buffer_valor = cheques_base * (premissas.BUFFER_CHEQUES / 100.0)
        demanda_ex_total = cheques_base + buffer_valor
        demanda_ex_aeronauta = demanda_ex_total * (premissas.PERC_EX_AERONAUTA / 100.0)
        demanda_ex_aeroviario = demanda_ex_total * (premissas.PERC_EX_AEROVIARIO / 100.0)
        return cheques_base, buffer_valor, demanda_ex_total, demanda_ex_aeronauta, demanda_ex_aeroviario

    @staticmethod
    def calcular_demanda_avaliadores(
        demanda_considerada: int,
        demanda_ex_total: float,
        premissas: PremissasModel
    ) -> Tuple[float, float, float]:
        demanda_ava_total = max(0.0, float(demanda_considerada) - demanda_ex_total)
        demanda_ava_aeroviario = demanda_ava_total * (premissas.PERC_AVA_AEROVIARIO / 100.0)
        demanda_ava_aeronauta = demanda_ava_total * (premissas.PERC_AVA_AERONAUTA / 100.0)
        return demanda_ava_total, demanda_ava_aeroviario, demanda_ava_aeronauta

    @staticmethod
    def converter_headcount_e_necessidade(
        demanda_ex_aeronauta: float,
        demanda_ex_aeroviario: float,
        demanda_ava_aeronauta: float,
        demanda_ava_aeroviario: float,
        premissas: PremissasModel
    ) -> Dict[str, float]:
        hc_bruto_ex_aero = demanda_ex_aeronauta / float(premissas.SESSAO_EX_AERONAUTA)
        hc_bruto_ex_viario = demanda_ex_aeroviario / float(premissas.SESSAO_EX_AEROVIARIO)
        hc_bruto_ava_aero = demanda_ava_aeronauta / float(premissas.SESSAO_AVA_AERONAUTA)
        hc_bruto_ava_viario = demanda_ava_aeroviario / float(premissas.SESSAO_AVA_AEROVIARIO)

        fator_ferias = premissas.FATOR_FERIAS_PERC / 100.0
        indisp_ferias_ex_aero = hc_bruto_ex_aero * fator_ferias
        indisp_ferias_ex_viario = hc_bruto_ex_viario * fator_ferias
        indisp_ferias_ava_aero = hc_bruto_ava_aero * fator_ferias
        indisp_ferias_ava_viario = hc_bruto_ava_viario * fator_ferias

        fator_trein = premissas.FATOR_TREINAMENTO_PERC / 100.0
        indisp_trein_ex_aero = hc_bruto_ex_aero * fator_trein
        indisp_trein_ex_viario = hc_bruto_ex_viario * fator_trein
        indisp_trein_ava_aero = hc_bruto_ava_aero * fator_trein
        indisp_trein_ava_viario = hc_bruto_ava_viario * fator_trein

        psm_ava_viario = float(premissas.PSM_AEROVIARIO)

        nec_ex_aeronauta = hc_bruto_ex_aero + indisp_ferias_ex_aero + indisp_trein_ex_aero
        nec_ex_aeroviario = hc_bruto_ex_viario + indisp_ferias_ex_viario + indisp_trein_ex_viario
        nec_ava_aeronauta = hc_bruto_ava_aero + indisp_ferias_ava_aero + indisp_trein_ava_aero
        nec_ava_aeroviario = hc_bruto_ava_viario + indisp_ferias_ava_viario + indisp_trein_ava_viario + psm_ava_viario

        return {
            "hc_bruto_ex_aeronauta": hc_bruto_ex_aero,
            "hc_bruto_ex_aeroviario": hc_bruto_ex_viario,
            "hc_bruto_ava_aeronauta": hc_bruto_ava_aero,
            "hc_bruto_ava_aeroviario": hc_bruto_ava_viario,
            "indisp_ferias_ex_aero": indisp_ferias_ex_aero,
            "indisp_ferias_ex_viario": indisp_ferias_ex_viario,
            "indisp_ferias_ava_aero": indisp_ferias_ava_aero,
            "indisp_ferias_ava_viario": indisp_ferias_ava_viario,
            "indisp_trein_ex_aero": indisp_trein_ex_aero,
            "indisp_trein_ex_viario": indisp_trein_ex_viario,
            "indisp_trein_ava_aero": indisp_trein_ava_aero,
            "indisp_trein_ava_viario": indisp_trein_ava_viario,
            "psm_ava_viario": psm_ava_viario,
            "nec_ex_aeronauta": nec_ex_aeronauta,
            "nec_ex_aeroviario": nec_ex_aeroviario,
            "nec_ava_aeronauta": nec_ava_aeronauta,
            "nec_ava_aeroviario": nec_ava_aeroviario
        }

    @staticmethod
    def projetar_disponibilidade(
        instrutores: List[InstrutorSchema],
        frota: str,
        ano_mes: str
    ) -> Dict[str, int]:
        ano_mes_norm = normalizar_ano_mes(ano_mes)
        ano, mes = map(int, ano_mes_norm.split("-"))
        primeiro_dia_mes = date(ano, mes, 1)
        _, ultimo_dia = calendar.monthrange(ano, mes)
        ultimo_dia_mes = date(ano, mes, ultimo_dia)

        disp_ex_aero = 0
        disp_ex_viario = 0
        disp_ava_aero = 0
        disp_ava_viario = 0

        for inst in instrutores:
            if inst.frota != frota:
                continue
            if inst.data_inicio and inst.data_inicio > ultimo_dia_mes:
                continue
            if inst.data_fim and inst.data_fim < primeiro_dia_mes:
                continue

            promovido_neste_mes = False
            if inst.movimentacao_prevista and "promocao" in inst.movimentacao_prevista.lower() and "examinador" in inst.movimentacao_prevista.lower():
                if inst.data_movimentacao and inst.data_movimentacao <= ultimo_dia_mes:
                    promovido_neste_mes = True

            eh_examinador = inst.examinador or promovido_neste_mes
            eh_avaliador = inst.avaliador or eh_examinador

            if inst.funcao == "Aeronauta":
                if eh_examinador:
                    disp_ex_aero += 1
                elif eh_avaliador:
                    disp_ava_aero += 1
            elif inst.funcao == "Aeroviario":
                if eh_examinador:
                    disp_ex_viario += 1
                elif eh_avaliador:
                    disp_ava_viario += 1

        return {
            "disp_ex_aeronauta": disp_ex_aero,
            "disp_ex_aeroviario": disp_ex_viario,
            "disp_ava_aeronauta": disp_ava_aero,
            "disp_ava_aeroviario": disp_ava_viario
        }

    @staticmethod
    def classificar_status_rag(saldo: float) -> str:
        if saldo < -1e-6:
            return "Vermelho"
        elif abs(saldo) <= 1e-6:
            return "Amarelo"
        else:
            return "Verde"

    @classmethod
    def processar_mes_frota(
        cls,
        frota: str,
        ano_mes: str,
        simulador: SimuladorSchema,
        demanda_real: int,
        periodicos_mes: float,
        staffing_itens: List[CrewStaffingItem],
        instrutores: List[InstrutorSchema],
        premissas: PremissasModel
    ) -> CalculoMensalFrota:
        ano_mes_norm = normalizar_ano_mes(ano_mes)
        mes_exibicao = formatar_ano_mes_exibicao(ano_mes_norm)

        cap_sim, dias_mes = cls.calcular_capacidade_simulador(
            simulador.qtd_dispositivos,
            simulador.slots_dia,
            ano_mes_norm
        )
        dem_cons, motivo_dem = cls.calcular_demanda_considerada(demanda_real, cap_sim)
        ch_anac_per, ch_cia_per = cls.calcular_cheques_periodicos(periodicos_mes)
        ch_staff = cls.segregar_cheques_staffing(staffing_itens, frota, ano_mes_norm)

        (
            ch_base,
            buf_val,
            dem_ex_total,
            dem_ex_aero,
            dem_ex_viario
        ) = cls.calcular_demanda_examinadores(
            ch_anac_per,
            ch_staff["total"],
            premissas
        )

        (
            dem_ava_total,
            dem_ava_viario,
            dem_ava_aero
        ) = cls.calcular_demanda_avaliadores(
            dem_cons,
            dem_ex_total,
            premissas
        )

        nec_dict = cls.converter_headcount_e_necessidade(
            dem_ex_aero,
            dem_ex_viario,
            dem_ava_aero,
            dem_ava_viario,
            premissas
        )

        disp_dict = cls.projetar_disponibilidade(instrutores, frota, ano_mes_norm)

        saldo_ex_aero = round(disp_dict["disp_ex_aeronauta"] - nec_dict["nec_ex_aeronauta"], 2)
        saldo_ex_viario = round(disp_dict["disp_ex_aeroviario"] - nec_dict["nec_ex_aeroviario"], 2)
        saldo_ava_aero = round(disp_dict["disp_ava_aeronauta"] - nec_dict["nec_ava_aeronauta"], 2)
        saldo_ava_viario = round(disp_dict["disp_ava_aeroviario"] - nec_dict["nec_ava_aeroviario"], 2)

        rag_ex_aero = cls.classificar_status_rag(saldo_ex_aero)
        rag_ex_viario = cls.classificar_status_rag(saldo_ex_viario)
        rag_ava_aero = cls.classificar_status_rag(saldo_ava_aero)
        rag_ava_viario = cls.classificar_status_rag(saldo_ava_viario)

        if any(r == "Vermelho" for r in [rag_ex_aero, rag_ex_viario, rag_ava_aero, rag_ava_viario]):
            rag_frota = "Vermelho"
        elif any(r == "Amarelo" for r in [rag_ex_aero, rag_ex_viario, rag_ava_aero, rag_ava_viario]):
            rag_frota = "Amarelo"
        else:
            rag_frota = "Verde"

        return CalculoMensalFrota(
            frota=frota,
            ano_mes=ano_mes_norm,
            mes_exibicao=mes_exibicao,
            dias_mes=dias_mes,
            qtd_dispositivos=simulador.qtd_dispositivos,
            slots_dia=simulador.slots_dia,
            capacidade_simulador=cap_sim,
            demanda_real=demanda_real,
            demanda_considerada=dem_cons,
            motivo_demanda_considerada=motivo_dem,
            periodicos_mes=round(periodicos_mes, 2),
            cheques_anac_periodicos=round(ch_anac_per, 2),
            cheques_cia_periodicos=round(ch_cia_per, 2),
            cheques_anac_movimentacao=ch_staff["total_movimentacao"],
            cheques_anac_transferencias=ch_staff["transferencias"],
            cheques_anac_upgrade=ch_staff["upgrade"],
            cheques_anac_new_hiring=ch_staff["new_hiring"],
            total_cheques_anac_staffing=ch_staff["total"],
            cheques_anac_base=round(ch_base, 2),
            buffer_cheques_valor=round(buf_val, 2),
            demanda_ex_total=round(dem_ex_total, 2),
            demanda_ex_aeronauta=round(dem_ex_aero, 2),
            demanda_ex_aeroviario=round(dem_ex_viario, 2),
            demanda_ava_total=round(dem_ava_total, 2),
            demanda_ava_aeroviario=round(dem_ava_viario, 2),
            demanda_ava_aeronauta=round(dem_ava_aero, 2),
            hc_bruto_ex_aeronauta=round(nec_dict["hc_bruto_ex_aeronauta"], 2),
            hc_bruto_ex_aeroviario=round(nec_dict["hc_bruto_ex_aeroviario"], 2),
            hc_bruto_ava_aeronauta=round(nec_dict["hc_bruto_ava_aeronauta"], 2),
            hc_bruto_ava_aeroviario=round(nec_dict["hc_bruto_ava_aeroviario"], 2),
            indisp_ferias_ex_aero=round(nec_dict["indisp_ferias_ex_aero"], 2),
            indisp_ferias_ex_viario=round(nec_dict["indisp_ferias_ex_viario"], 2),
            indisp_ferias_ava_aero=round(nec_dict["indisp_ferias_ava_aero"], 2),
            indisp_ferias_ava_viario=round(nec_dict["indisp_ferias_ava_viario"], 2),
            indisp_trein_ex_aero=round(nec_dict["indisp_trein_ex_aero"], 2),
            indisp_trein_ex_viario=round(nec_dict["indisp_trein_ex_viario"], 2),
            indisp_trein_ava_aero=round(nec_dict["indisp_trein_ava_aero"], 2),
            indisp_trein_ava_viario=round(nec_dict["indisp_trein_ava_viario"], 2),
            psm_ava_viario=round(nec_dict["psm_ava_viario"], 2),
            nec_ex_aeronauta=round(nec_dict["nec_ex_aeronauta"], 2),
            nec_ex_aeroviario=round(nec_dict["nec_ex_aeroviario"], 2),
            nec_ava_aeronauta=round(nec_dict["nec_ava_aeronauta"], 2),
            nec_ava_aeroviario=round(nec_dict["nec_ava_aeroviario"], 2),
            disp_ex_aeronauta=disp_dict["disp_ex_aeronauta"],
            disp_ex_aeroviario=disp_dict["disp_ex_aeroviario"],
            disp_ava_aeronauta=disp_dict["disp_ava_aeronauta"],
            disp_ava_aeroviario=disp_dict["disp_ava_aeroviario"],
            saldo_ex_aeronauta=round(saldo_ex_aero, 2),
            saldo_ex_aeroviario=round(saldo_ex_viario, 2),
            saldo_ava_aeronauta=round(saldo_ava_aero, 2),
            saldo_ava_aeroviario=round(saldo_ava_viario, 2),
            status_rag_ex_aero=rag_ex_aero,
            status_rag_ex_viario=rag_ex_viario,
            status_rag_ava_aero=rag_ava_aero,
            status_rag_ava_viario=rag_ava_viario,
            status_rag_frota=rag_frota
        )