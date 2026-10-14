"""
Script de Homologação Operacional do SIPCAP.

Objetivos:
1. Carregar automaticamente todas as bases reais (.xlsx prioritário ou .csv).
2. Executar o pipeline analítico completo da Fase 2 para todas as frotas e períodos.
3. Gerar 3 arquivos Excel para conferência:
   - resultado_consolidado.xlsx (Visão Executiva, Matriz Necessidade x Disponibilidade e Saldos)
   - recomendacoes.xlsx:
     * Recomendacoes_Operacionais (Ações operacionais mês a mês)
     * Necessidade_Estrategica_Consolidada (Recomendação estratégica ÚNICA por Frota e Função)
     * Cobertura_Cruzada_Consolidada (Visão consolidada executiva da RN-12)
     * Cobertura_Cruzada_RN12 (Detalhamento mensal de cobertura cruzada para auditoria)
   - auditoria.xlsx (Memória detalhada de cálculo)
"""
import sys
from pathlib import Path
from typing import Dict
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.engine.orchestrator import SIPCAPOrchestrator


def obter_caminho_tabela(nome_base: str) -> Path:
    p_xlsx = ROOT_DIR / "data" / "raw" / f"{nome_base}.xlsx"
    if p_xlsx.exists():
        return p_xlsx
    p_csv = ROOT_DIR / "data" / "raw" / f"{nome_base}.csv"
    if p_csv.exists():
        return p_csv
    return p_xlsx


def exportar_excel_com_fallback(df: pd.DataFrame, caminho_arquivo: Path) -> Path:
    try:
        df.to_excel(caminho_arquivo, index=False, engine="openpyxl")
        return caminho_arquivo
    except Exception:
        try:
            df.to_excel(caminho_arquivo, index=False)
            return caminho_arquivo
        except Exception:
            caminho_csv = caminho_arquivo.with_suffix(".csv")
            df.to_csv(caminho_csv, index=False, sep=";", encoding="utf-8-sig")
            return caminho_csv


def exportar_excel_multi_abas_com_fallback(
    abas_dict: Dict[str, pd.DataFrame],
    caminho_arquivo: Path
) -> Path:
    try:
        with pd.ExcelWriter(caminho_arquivo, engine="openpyxl") as writer:
            for nome_aba, df in abas_dict.items():
                df.to_excel(writer, sheet_name=nome_aba[:31], index=False)
        return caminho_arquivo
    except Exception:
        for i, (nome_aba, df) in enumerate(abas_dict.items()):
            if i == 0:
                p_saida = caminho_arquivo.with_suffix(".csv")
            else:
                sufixo = nome_aba.lower().replace(" ", "_").replace("ç", "c").replace("õ", "o").replace("ê", "e").replace("á", "a")
                p_saida = caminho_arquivo.parent / f"{caminho_arquivo.stem}_{sufixo}.csv"
            df.to_csv(p_saida, index=False, sep=";", encoding="utf-8-sig")
        return caminho_arquivo.with_suffix(".csv")


def main():
    print("=" * 70)
    print(" SIPCAP - EXECUÇÃO DE HOMOLOGAÇÃO OPERACIONAL (FASE 2)")
    print("=" * 70)

    # 1. Resolução dos caminhos de entrada
    caminho_premissas = obter_caminho_tabela("tbl_premissas")
    caminho_simuladores = obter_caminho_tabela("tbl_simuladores")
    caminho_demanda = obter_caminho_tabela("tbl_demanda_slots")
    caminho_staffing = obter_caminho_tabela("tbl_crew_staffing")
    caminho_instrutores = obter_caminho_tabela("tbl_instrutores")

    print("\n[1/3] Carregando bases reais de entrada:")
    print(f"  • Premissas:    {caminho_premissas.name}")
    print(f"  • Simuladores:  {caminho_simuladores.name}")
    print(f"  • Demanda:      {caminho_demanda.name}")
    print(f"  • Staffing:     {caminho_staffing.name}")
    print(f"  • Instrutores:  {caminho_instrutores.name}")

    orquestrador = SIPCAPOrchestrator.carregar_de_arquivos(
        caminho_premissas,
        caminho_simuladores,
        caminho_demanda,
        caminho_staffing,
        caminho_instrutores
    )

    print(f"\n  Premissas Ativas de Capacidade:")
    print(f"  - Fator Férias: {orquestrador.premissas.FATOR_FERIAS_PERC}%")
    print(f"  - Fator Treinamento Próprio: {orquestrador.premissas.FATOR_TREINAMENTO_PERC}% (13 dias/ano)")
    print(f"  - Populações por Frota: {orquestrador.premissas.POPULACOES_FROTA or f'Padrão {orquestrador.premissas.POPULACAO_PERIODICOS_PADRAO}'}")

    # 2. Execução analítica
    print("\n[2/3] Executando pipeline analítico completo...")
    orquestrador.executar()

    print(f"  ✓ {len(orquestrador.calculos)} projeções mensais calculadas.")
    print(f"  ✓ {len(orquestrador.coberturas_cruzadas)} análises de Cobertura Cruzada pontual (RN-12) processadas.")
    print(f"  ✓ {len(orquestrador.recomendacoes)} recomendações operacionais geradas.")
    print(f"  ✓ {len(orquestrador.necessidades_estrategicas_consolidadas)} recomendações estratégicas consolidadas geradas (1 por Frota/Função).")

    # 3. Exportações
    print("\n[3/3] Gerando arquivos Excel para homologação:")

    # 3.1 resultado_consolidado.xlsx
    dados_consolidados = []
    for c in orquestrador.calculos:
        dados_consolidados.append({
            "Frota": c.frota,
            "Ano_Mes": c.ano_mes,
            "Mês": c.mes_exibicao,
            "Capacidade_Simulador": c.capacidade_simulador,
            "Demanda_Real": c.demanda_real,
            "Demanda_Considerada": c.demanda_considerada,
            "Nec_EX_Aeronauta": c.nec_ex_aeronauta,
            "Nec_EX_Aeroviario": c.nec_ex_aeroviario,
            "Nec_AVA_Aeronauta": c.nec_ava_aeronauta,
            "Nec_AVA_Aeroviario": c.nec_ava_aeroviario,
            "Necessidade_Total": round(c.nec_ex_aeronauta + c.nec_ex_aeroviario + c.nec_ava_aeronauta + c.nec_ava_aeroviario, 2),
            "Disp_EX_Aeronauta": c.disp_ex_aeronauta,
            "Disp_EX_Aeroviario": c.disp_ex_aeroviario,
            "Disp_AVA_Aeronauta": c.disp_ava_aeronauta,
            "Disp_AVA_Aeroviario": c.disp_ava_aeroviario,
            "Disponibilidade_Total": c.disp_ex_aeronauta + c.disp_ex_aeroviario + c.disp_ava_aeronauta + c.disp_ava_aeroviario,
            "Saldo_EX_Aeronauta": c.saldo_ex_aeronauta,
            "Saldo_EX_Aeroviario": c.saldo_ex_aeroviario,
            "Saldo_AVA_Aeronauta": c.saldo_ava_aeronauta,
            "Saldo_AVA_Aeroviario": c.saldo_ava_aeroviario,
            "Saldo_Consolidado": round(c.saldo_ex_aeronauta + c.saldo_ex_aeroviario + c.saldo_ava_aeronauta + c.saldo_ava_aeroviario, 2),
            "RAG_EX_Aero": c.status_rag_ex_aero,
            "RAG_EX_Viario": c.status_rag_ex_viario,
            "RAG_AVA_Aero": c.status_rag_ava_aero,
            "RAG_AVA_Viario": c.status_rag_ava_viario,
            "Status_Frota": c.status_rag_frota,
        })
    df_consolidado = pd.DataFrame(dados_consolidados)
    caminho_res = ROOT_DIR / "resultado_consolidado.xlsx"
    arq_res = exportar_excel_com_fallback(df_consolidado, caminho_res)
    print(f"  • {arq_res.name} ({len(df_consolidado)} linhas geradas)")

    # 3.2 recomendacoes.xlsx
    # Aba 1: Recomendações Operacionais (Mês a Mês)
    dados_rec = []
    for r in orquestrador.recomendacoes:
        dados_rec.append({
            "Frota": r.frota,
            "Mês_Evento": r.ano_mes_evento,
            "Mês_Exibição": r.mes_exibicao,
            "Função": r.funcao,
            "Déficit_Original": r.deficit_original,
            "Cobertura_Cruzada_Ativa": "Sim" if r.cobertura_cruzada else "Não",
            "Déficit_Remanescente": r.deficit_remanescente,
            "Prioridade": r.prioridade,
            "Ação_Recomendada": r.acao_recomendada,
            "Mês_Limite_Início": r.mes_limite_inicio,
            "Mês_Limite_Exibição": r.mes_limite_exibicao,
            "Antecedência_Meses": r.antecedencia_meses,
        })
    df_recomendacoes = pd.DataFrame(dados_rec)

    # Aba 2: Necessidade Estratégica Consolidada (1 linha por Frota/Função)
    dados_est_cons = []
    for e in orquestrador.necessidades_estrategicas_consolidadas:
        dados_est_cons.append({
            "Frota": e.frota,
            "Função": e.funcao,
            "Período_Planejamento": e.periodo_analisado,
            "Total_Meses": e.total_meses,
            "Déficit_Pico": e.deficit_pico,
            "Déficit_Médio": e.deficit_medio,
            "Déficit_Mediano": e.deficit_mediano,
            "Meses_Críticos": f"{e.meses_criticos_count} de {e.total_meses}",
            "Cobertura_Cruzada_Média": e.cobertura_cruzada_media,
            "Déficit_Líquido_Estratégico": e.deficit_liquido_estrategico,
            "Formação_Estratégica_Sugerida": e.formacao_estrategica_sugerida,
            "Diagnóstico_Estratégico": e.diagnostico_estrategico,
        })
    df_estrategico_consolidado = pd.DataFrame(dados_est_cons)

    # Aba 3: Cobertura Cruzada Consolidada (RN-12)
    dados_cob_cons = []
    for c in orquestrador.coberturas_cruzadas_consolidadas:
        dados_cob_cons.append({
            "Frota": c.frota,
            "Função": c.funcao,
            "Período_Planejamento": c.periodo_analisado,
            "Déficit_Médio": c.deficit_medio,
            "Capacidade_Média_Cobertura": c.capacidade_media_cobertura,
            "Déficit_Líquido_Estratégico": c.deficit_liquido_estrategico,
            "Percentual_Cobertura_Média": f"{c.percentual_cobertura_media:.1f}%",
            "Diagnóstico": c.diagnostico,
        })
    df_cob_consolidada = pd.DataFrame(dados_cob_cons)

    # Aba 4: Coberturas Cruzadas Pontuais RN-12 (Mês a Mês)
    dados_cob_det = []
    for c in orquestrador.coberturas_cruzadas:
        dados_cob_det.append({
            "Frota": c.frota,
            "Ano_Mes": c.ano_mes,
            "Mês_Exibição": c.mes_exibicao,
            "Função_Deficitária": c.funcao_deficitaria,
            "Função_Superavitária": c.funcao_superavitaria,
            "Déficit_Original": c.deficit_original,
            "Superávit_Disponível": c.superavit_disponivel,
            "Capacidade_Cobertura": c.capacidade_cobertura,
            "Percentual_Cobertura": c.percentual_cobertura,
            "Tipo_Cobertura": c.tipo_cobertura,
            "Déficit_Remanescente": c.deficit_remanescente,
            "Diagnóstico": c.mensagem_diagnostico,
        })
    df_coberturas_det = pd.DataFrame(dados_cob_det)

    abas_recomendacoes = {
        "Recomendacoes_Operacionais": df_recomendacoes,
        "Necessidade_Estrategica_Consolidada": df_estrategico_consolidado,
        "Cobertura_Cruzada_Consolidada": df_cob_consolidada,
        "Cobertura_Cruzada_RN12": df_coberturas_det,
    }
    caminho_rec = ROOT_DIR / "recomendacoes.xlsx"
    arq_rec = exportar_excel_multi_abas_com_fallback(abas_recomendacoes, caminho_rec)
    print(f"  • {arq_rec.name} ({len(df_recomendacoes)} operacionais | {len(df_estrategico_consolidado)} estratégicas consolidadas)")

    # 3.3 auditoria.xlsx
    df_auditoria = orquestrador.dataframe_auditoria
    caminho_aud = ROOT_DIR / "auditoria.xlsx"
    arq_aud = exportar_excel_com_fallback(df_auditoria, caminho_aud)
    print(f"  • {arq_aud.name} ({len(df_auditoria)} linhas com segregação de cheques, férias e treinamentos)")

    # Resumo em tela
    print("\n" + "=" * 70)
    print(" RESUMO EXECUTIVO POR FROTA")
    print("=" * 70)
    df_status = orquestrador.obter_status_executivo_frotas()
    print(df_status.to_string(index=False))

    # Tabela Executiva Consolidada de Formação
    print("\n" + "=" * 105)
    print(" NECESSIDADE ESTRATÉGICA CONSOLIDADA DE FORMAÇÃO (RECOMENDAÇÃO FINAL ÚNICA POR FROTA E FUNÇÃO)")
    print("=" * 105)
    cols_exib = [
        "Frota", "Função", "Déficit_Pico", "Déficit_Médio",
        "Déficit_Mediano", "Meses_Críticos", "Cobertura_Cruzada_Média",
        "Déficit_Líquido_Estratégico", "Formação_Estratégica_Sugerida"
    ]
    print(df_estrategico_consolidado[cols_exib].to_string(index=False))

    print("\n" + "=" * 105)
    print(" RESUMO CONSOLIDADO DE COBERTURA CRUZADA (RN-12)")
    print("=" * 105)
    cols_cob_exib = [
        "Frota", "Função", "Déficit_Médio",
        "Capacidade_Média_Cobertura", "Déficit_Líquido_Estratégico", "Percentual_Cobertura_Média"
    ]
    print(df_cob_consolidada[cols_cob_exib].to_string(index=False))

    print("\n✓ Homologação concluída com sucesso! Os arquivos foram gerados na raiz do projeto.")
    print("=" * 105)


if __name__ == "__main__":
    main()