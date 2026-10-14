"""
Bateria de Testes Automatizados - FASE 2 SIPCAP
Validação da Matemática Analítica, Motor de Capacidade, Auditoria,
Promoção de Instrutores e Cobertura Cruzada RN-12.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.loaders.data_loader import DataLoader
from src.domain.schemas import (
    SimuladorSchema,
    PremissasModel,
    CrewStaffingItem,
    InstrutorSchema,
    CalculoMensalFrota
)
from src.domain.enums import TipoStaffingEnum
from src.engine.capacity_engine import CapacityEngine
from src.engine.recommendation_engine import RecommendationEngine
from src.engine.audit_engine import AuditEngine
from src.engine.orchestrator import SIPCAPOrchestrator


def obter_caminho_tabela(nome_base: str) -> Path:
    """Busca prioritariamente .xlsx; se não existir, tenta .csv."""
    p_xlsx = ROOT_DIR / "data" / "raw" / f"{nome_base}.xlsx"
    if p_xlsx.exists():
        return p_xlsx
    p_csv = ROOT_DIR / "data" / "raw" / f"{nome_base}.csv"
    if p_csv.exists():
        return p_csv
    return p_xlsx


def test_exemplo_numerico_ponta_a_ponta():
    print("--- [TESTE 1] Validação Numérica Ponta a Ponta Passo a Passo ---")
    premissas = PremissasModel(
        SESSAO_AVA_AERONAUTA=7,
        SESSAO_AVA_AEROVIARIO=14,
        SESSAO_EX_AERONAUTA=7,
        SESSAO_EX_AEROVIARIO=14,
        BUFFER_CHEQUES=20.0,
        PERC_EX_AERONAUTA=70.0,
        PERC_EX_AEROVIARIO=30.0,
        PERC_AVA_AEROVIARIO=70.0,
        PERC_AVA_AERONAUTA=30.0,
        PRAZO_FORMACAO_AVALIADOR=3,
        OFFSET_CHEQUE_MOVIMENTACAO=2,
        PSM_AEROVIARIO=2,
        MESES_ALTA="JAN,JUL,DEZ",
        PERC_ALTA=60.0,
        FATOR_FERIAS_PERC=8.33,
        FATOR_TREINAMENTO_PERC=0.0,
        POPULACAO_PERIODICOS_PADRAO=840,
        CAPACIDADE_RATIO_AEROVIARIO=2.0
    )

    ano_mes = "2027-03"
    simulador = SimuladorSchema(frota="ERJ", qtd_dispositivos=2, slots_dia=5)

    # 1. Capacidade Simulador
    cap_sim = CapacityEngine.calcular_capacidade_simulador(ano_mes, 2, 5)
    assert cap_sim == 310

    # 2. Demanda Considerada
    dem_cons, motivo = CapacityEngine.calcular_demanda_considerada(390, cap_sim)
    assert dem_cons == 390

    # 3. Periódicos
    dist = CapacityEngine.distribuir_treinamentos_periodicos(2027, 840.0, premissas)
    assert round(dist["2027-01"], 2) == 42.0
    assert round(dist["2027-03"], 2) == 79.33
    periodicos_marco = dist["2027-03"]

    # 4 e 5. Cheques ANAC e CIA
    chq_anac_per, chq_cia_per = CapacityEngine.calcular_cheques_periodicos(periodicos_marco)
    assert round(chq_anac_per, 2) == 79.33
    assert round(chq_cia_per, 2) == 79.33

    # 6, 7 e 8. Staffing
    itens_staffing = [
        CrewStaffingItem(
            career_move_original="FO ATR -> CA ERJ",
            tipo_evento=TipoStaffingEnum.MOVIMENTACAO,
            frota_destino="ERJ",
            ano_mes_entrada="2027-01",
            qtd_tripulantes=2,
            offset_meses=2,
            ano_mes_cheque="2027-03",
            cheques_gerados=4
        ),
        CrewStaffingItem(
            career_move_original="FO ERJ -> CA ERJ",
            tipo_evento=TipoStaffingEnum.UPGRADE,
            frota_destino="ERJ",
            ano_mes_entrada="2027-01",
            qtd_tripulantes=3,
            offset_meses=2,
            ano_mes_cheque="2027-03",
            cheques_gerados=6
        ),
        CrewStaffingItem(
            career_move_original="ERJ - New Hiring",
            tipo_evento=TipoStaffingEnum.NEW_HIRING,
            frota_destino="ERJ",
            ano_mes_entrada="2027-01",
            qtd_tripulantes=5,
            offset_meses=2,
            ano_mes_cheque="2027-03",
            cheques_gerados=10
        ),
    ]
    seg = CapacityEngine.segregar_cheques_staffing(itens_staffing, "ERJ", "2027-03")
    assert seg["movimentacao"] == 4
    assert seg["upgrade"] == 6
    assert seg["new_hiring"] == 10
    assert seg["total"] == 20

    # 9 e 10. Demanda Examinadores e Buffer
    chq_base, buf_val, dem_ex_tot, dem_ex_aero, dem_ex_viario = CapacityEngine.calcular_demanda_examinadores(
        chq_anac_per,
        seg["total"],
        premissas
    )
    assert round(chq_base, 2) == 99.33
    assert round(buf_val, 2) == 19.87
    assert round(dem_ex_tot, 2) == 119.20
    assert round(dem_ex_aero, 2) == 83.44
    assert round(dem_ex_viario, 2) == 35.76

    # 11. Demanda Avaliadores
    dem_ava_tot, dem_ava_viario, dem_ava_aero = CapacityEngine.calcular_demanda_avaliadores(
        dem_cons,
        dem_ex_tot,
        premissas
    )
    assert round(dem_ava_tot, 2) == 270.80
    assert round(dem_ava_viario, 2) == 189.56
    assert round(dem_ava_aero, 2) == 81.24

    # 12, 13, 14, 15, 16. Headcount, Indisponibilidade e PSM
    nec = CapacityEngine.converter_headcount_e_necessidade(
        dem_ex_aero,
        dem_ex_viario,
        dem_ava_aero,
        dem_ava_viario,
        premissas
    )
    assert round(nec["hc_bruto_ex_aeronauta"], 2) == 11.92
    assert round(nec["hc_bruto_ex_aeroviario"], 2) == 2.55
    assert round(nec["hc_bruto_ava_aeronauta"], 2) == 11.61
    assert round(nec["hc_bruto_ava_aeroviario"], 2) == 13.54
    assert round(nec["nec_ex_aeronauta"], 2) == 12.91
    assert round(nec["nec_ava_aeroviario"], 2) == 16.67

    print("✓ Exemplo numérico validado com precisão analítica absoluta.")


def test_promocao_avaliador_para_examinador():
    print("--- [TESTE 2] Regra de Promoção de Avaliador para Examinador (-1 AVA, +1 EX) ---")
    instrutores = [
        InstrutorSchema(
            re="370",
            nome="Instrutor 1",
            frota="ERJ",
            funcao="Aeronauta",
            avaliador=True,
            examinador=False
        ),
        InstrutorSchema(
            re="749",
            nome="Instrutor 2",
            frota="ERJ",
            funcao="Aeronauta",
            avaliador=True,
            examinador=False,
            movimentacao_prevista="Promocao_Examinador",
            data_movimentacao="2027-04-01"
        )
    ]

    disp_mar = CapacityEngine.projetar_disponibilidade(instrutores, "ERJ", "2027-03")
    assert disp_mar["disp_ava_aeronauta"] == 2
    assert disp_mar["disp_ex_aeronauta"] == 0

    disp_abr = CapacityEngine.projetar_disponibilidade(instrutores, "ERJ", "2027-04")
    assert disp_abr["disp_ava_aeronauta"] == 1
    assert disp_abr["disp_ex_aeronauta"] == 1

    print("✓ Regra de transição de status (+1 EX, -1 AVA) validada com sucesso.")


def test_cobertura_cruzada_rn12():
    print("--- [TESTE 3] Validação da RN-12 (Cobertura Cruzada Aeronauta x Aeroviário) ---")
    # Caso Integral (1 Aeroviário cobre 2 Aeronautas)
    res_integral = RecommendationEngine.analisar_cobertura_cruzada_funcao(
        frota="ERJ",
        ano_mes="2027-07",
        mes_exibicao="Jul/27",
        funcao_grupo="Avaliador",
        saldo_aeronauta=-2.0,
        saldo_aeroviario=1.0,
        ratio_aeroviario=2.0
    )
    assert res_integral is not None
    assert res_integral.tipo_cobertura == "Integral"
    assert res_integral.percentual_cobertura == 100.0
    assert res_integral.deficit_remanescente == 0.0

    # Caso Parcial (1 Aeronauta cobre 0.5 Aeroviário)
    res_parcial = RecommendationEngine.analisar_cobertura_cruzada_funcao(
        frota="A320",
        ano_mes="2027-08",
        mes_exibicao="Ago/27",
        funcao_grupo="Avaliador",
        saldo_aeronauta=1.0,
        saldo_aeroviario=-1.0,
        ratio_aeroviario=2.0
    )
    assert res_parcial is not None
    assert res_parcial.tipo_cobertura == "Parcial"
    assert res_parcial.percentual_cobertura == 50.0
    assert res_parcial.deficit_remanescente == 0.5

    print("✓ RN-12 (Cobertura Cruzada Integral e Parcial) validada com total precisão.")


def test_pipeline_completo_e_auditoria():
    print("--- [TESTE 4] Pipeline Completo Integrado e Geração de Auditoria ---")
    caminho_premissas = obter_caminho_tabela("tbl_premissas")
    caminho_simuladores = obter_caminho_tabela("tbl_simuladores")
    caminho_demanda = obter_caminho_tabela("tbl_demanda_slots")
    caminho_staffing = obter_caminho_tabela("tbl_crew_staffing")
    caminho_instrutores = obter_caminho_tabela("tbl_instrutores")

    orquestrador = SIPCAPOrchestrator.carregar_de_arquivos(
        caminho_premissas,
        caminho_simuladores,
        caminho_demanda,
        caminho_staffing,
        caminho_instrutores
    )

    orquestrador.executar()

    assert len(orquestrador.calculos) > 0, "Nenhum cálculo gerado"
    df_aud = orquestrador.dataframe_auditoria
    assert not df_aud.empty

    colunas_obrigatorias = [
        "Cheques_ANAC_Periodicos",
        "Cheques_ANAC_Movimentacao",
        "Cheques_ANAC_Upgrade",
        "Cheques_ANAC_New_Hiring",
        "Total_Cheques_Staffing",
        "Buffer_Cheques_ANAC",
        "Demanda_Considerada",
        "Motivo_Demanda"
    ]
    for col in colunas_obrigatorias:
        assert col in df_aud.columns, f"Coluna de auditoria ausente: {col}"

    df_resumo = orquestrador.obter_status_executivo_frotas()
    assert len(df_resumo) > 0
    assert "Status" in df_resumo.columns

    print(f"✓ Pipeline gerou {len(orquestrador.calculos)} meses analisados, "
          f"{len(orquestrador.coberturas_cruzadas)} cruzamentos e "
          f"{len(orquestrador.recomendacoes)} recomendações prescritivas.")


if __name__ == "__main__":
    print("=" * 60)
    print(" INICIANDO TESTES DE HOMOLOGAÇÃO DA FASE 2 - SIPCAP")
    print("=" * 60)
    test_exemplo_numerico_ponta_a_ponta()
    test_promocao_avaliador_para_examinador()
    test_cobertura_cruzada_rn12()
    test_pipeline_completo_e_auditoria()
    print("=" * 60)
    print(" TODOS OS TESTES DA FASE 2 PASSARAM COM 100% DE SUCESSO!")
    print("=" * 60)