"""
Bateria de Testes Automatizados - FASE 1 SIPCAP
Validação Genérica e Dinâmica de Dados, Schemas e Parser de Crew Staffing.
Compatível tanto com bases reais de produção (.xlsx) quanto com bases de homologação (.csv).
"""
import sys
import re
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.loaders.data_loader import DataLoader
from src.parsers.staffing_parser import CrewStaffingParser
from src.domain.enums import TipoStaffingEnum
from src.domain.schemas import PremissasModel
from src.utils.date_utils import adicionar_meses


def obter_caminho_tabela(nome_base: str) -> Path:
    """Busca prioritariamente o arquivo .xlsx; se não existir, busca o .csv."""
    p_xlsx = ROOT_DIR / "data" / "raw" / f"{nome_base}.xlsx"
    if p_xlsx.exists():
        return p_xlsx
    p_csv = ROOT_DIR / "data" / "raw" / f"{nome_base}.csv"
    if p_csv.exists():
        return p_csv
    return p_xlsx


def test_carregamento_premissas():
    print("--- [TESTE 1] Carregamento e Validação da tbl_premissas ---")
    caminho = obter_caminho_tabela("tbl_premissas")
    premissas = DataLoader.carregar_premissas(caminho)

    assert premissas.SESSAO_AVA_AERONAUTA > 0, "SESSAO_AVA_AERONAUTA deve ser > 0"
    assert premissas.SESSAO_AVA_AEROVIARIO > 0, "SESSAO_AVA_AEROVIARIO deve ser > 0"
    assert premissas.SESSAO_EX_AERONAUTA > 0, "SESSAO_EX_AERONAUTA deve ser > 0"
    assert premissas.SESSAO_EX_AEROVIARIO > 0, "SESSAO_EX_AEROVIARIO deve ser > 0"
    assert premissas.PRAZO_FORMACAO_AVALIADOR > 0, "PRAZO_FORMACAO_AVALIADOR deve ser > 0"
    assert premissas.OFFSET_CHEQUE_MOVIMENTACAO >= 0, "OFFSET_CHEQUE_MOVIMENTACAO deve ser >= 0"

    assert round(premissas.PERC_EX_AERONAUTA + premissas.PERC_EX_AEROVIARIO, 1) == 100.0
    assert round(premissas.PERC_AVA_AEROVIARIO + premissas.PERC_AVA_AERONAUTA, 1) == 100.0
    assert not hasattr(premissas, "PRAZO_FORMACAO_EXAMINADOR"), "PRAZO_FORMACAO_EXAMINADOR não deve existir na V1"

    print(f"✓ tbl_premissas carregada e validada com sucesso ({caminho.name}).")
    return premissas


def test_carregamento_instrutores():
    print("--- [TESTE 2] Carregamento e Validação da tbl_instrutores ---")
    caminho = obter_caminho_tabela("tbl_instrutores")
    instrutores = DataLoader.carregar_instrutores(caminho)

    assert len(instrutores) > 0, f"A tabela {caminho.name} está vazia ou não pôde ser lida."

    for inst in instrutores:
        assert isinstance(inst.re, str) and len(inst.re) > 0, f"RE inválido para instrutor: {inst.nome}"
        assert inst.frota in ["ERJ", "A320", "ATR", "A330", "B737"], f"Frota não mapeada: {inst.frota}"
        assert inst.funcao in ["Aeronauta", "Aeroviario"], f"Função inválida: {inst.funcao}"

        if inst.examinador:
            assert inst.avaliador is True, f"Instrutor {inst.nome} (RE {inst.re}) é examinador mas não avaliador!"

    print(f"✓ {len(instrutores)} instrutores carregados e validados com sucesso ({caminho.name}).")


def test_carregamento_simuladores():
    print("--- [TESTE 3] Carregamento e Validação da tbl_simuladores ---")
    caminho = obter_caminho_tabela("tbl_simuladores")
    simuladores = DataLoader.carregar_simuladores(caminho)

    assert len(simuladores) > 0, f"A tabela {caminho.name} está vazia."
    for sim in simuladores:
        assert sim.qtd_dispositivos > 0, f"Qtd dispositivos inválida na frota {sim.frota}"
        assert sim.slots_dia > 0, f"Slots/dia inválido na frota {sim.frota}"

    frotas_cadastradas = [s.frota for s in simuladores]
    print(f"✓ {len(simuladores)} configurações de simulador validadas: {frotas_cadastradas} ({caminho.name}).")


def test_carregamento_demanda_slots():
    print("--- [TESTE 4] Carregamento e Normalização da tbl_demanda_slots ---")
    caminho = obter_caminho_tabela("tbl_demanda_slots")
    demandas = DataLoader.carregar_demanda_slots(caminho)

    assert len(demandas) > 0, f"A tabela {caminho.name} está vazia."

    for d in demandas:
        assert re.match(r"^\d{4}-\d{2}$", d.mes), f"Mês não normalizado para YYYY-MM: '{d.mes}' na frota {d.frota}"
        assert d.demanda_slots >= 0, f"Demanda negativa ({d.demanda_slots}) na frota {d.frota}, mês {d.mes}"

    print(f"✓ {len(demandas)} registros de demanda de slots validados com normalização canônica YYYY-MM ({caminho.name}).")


def test_parser_crew_staffing(premissas: PremissasModel):
    print("--- [TESTE 5] Validação Genérica do Parser de Crew Staffing ---")
    caminho = obter_caminho_tabela("tbl_crew_staffing")
    itens = DataLoader.carregar_crew_staffing(caminho, premissas)

    assert len(itens) > 0, f"Nenhuma transição identificada na tabela {caminho.name}."

    offset_esperado = premissas.OFFSET_CHEQUE_MOVIMENTACAO
    frotas_destino_encontradas = set()
    tipos_encontrados = set()

    for item in itens:
        # 1. Validação de RN-06: Cada tripulante gera exatamente 2 cheques operacionais
        assert item.cheques_gerados == item.qtd_tripulantes * 2, (
            f"Violação da RN-06: {item.qtd_tripulantes} tripulantes geraram {item.cheques_gerados} cheques (esperado 2x)"
        )

        # 2. Validação da aplicação do Offset temporal
        mes_esperado = adicionar_meses(item.ano_mes_entrada, offset_esperado)
        assert item.ano_mes_cheque == mes_esperado, (
            f"Offset incorreto: entrada {item.ano_mes_entrada} gerou cheque em {item.ano_mes_cheque} (esperado {mes_esperado})"
        )

        # 3. Validação de frota destino válida e identificada
        assert item.frota_destino is not None and len(item.frota_destino) > 0, (
            f"Frota destino não identificada no registro: {item.career_move_original}"
        )
        frotas_destino_encontradas.add(item.frota_destino)

        # 4. Validação da interpretação de tipos (TipoStaffingEnum válido)
        assert isinstance(item.tipo_evento, TipoStaffingEnum), f"Tipo inválido: {item.tipo_evento}"
        tipos_encontrados.add(item.tipo_evento.value)

    # 5. Geração e validação do Resumo de Auditoria Segregado
    parser = CrewStaffingParser()
    resumo_auditoria = parser.consolidar_para_auditoria(itens)

    print(f"\n✓ Total de alocações mensais processadas: {len(itens)}")
    print(f"✓ Frotas de destino identificadas: {sorted(list(frotas_destino_encontradas))}")
    print(f"✓ Tipos de evento classificados: {sorted(list(tipos_encontrados))}")
    print("\n--- Amostra do Resumo de Auditoria Consolidado (Top 10) ---")
    print(resumo_auditoria.head(10).to_string(index=False))
    print(f"\n✓ Parser do Crew Staffing homologado com sucesso em {caminho.name}!")


if __name__ == "__main__":
    print("=" * 60)
    print(" INICIANDO TESTES DE HOMOLOGAÇÃO DA FASE 1 - SIPCAP")
    print("=" * 60)
    premissas = test_carregamento_premissas()
    test_carregamento_instrutores()
    test_carregamento_simuladores()
    test_carregamento_demanda_slots()
    test_parser_crew_staffing(premissas)
    print("=" * 60)
    print(" TODOS OS TESTES DA FASE 1 PASSARAM COM SUCESSO!")
    print("=" * 60)