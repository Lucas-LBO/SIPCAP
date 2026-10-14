"""
Tela 1 – Dashboard Executivo do SIPCAP.

Objetivo:
Exibir rapidamente a situação de cada frota para a alta gestão:
- Status RAG (Verde / Amarelo / Vermelho)
- Menor saldo encontrado no horizonte
- Função mais crítica
- Quantidade de meses críticos
- Formação estratégica recomendada
"""
import pandas as pd
import streamlit as st
from typing import Dict, Any, List

from components.cards import (
    render_metric_card,
    render_rag_badge,
    render_card_frota_executiva
)
from src.engine.orchestrator import SIPCAPOrchestrator


def render_view_dashboard(orquestrador: SIPCAPOrchestrator) -> None:
    st.title("📊 Dashboard Executivo de Capacidade")
    st.markdown(
        "Visão executiva da saúde operacional das frotas de simuladores, "
        "indicando status RAG, criticidade e plano estratégico de formação sustentada."
    )
    st.markdown("---")

    # 1. Carrega dados consolidados do motor
    df_status = orquestrador.obter_status_executivo_frotas()
    df_auditoria = orquestrador.dataframe_auditoria
    necessidades_est = orquestrador.necessidades_estrategicas_consolidadas

    if df_status.empty:
        st.warning("Nenhum dado de capacidade disponível para exibição.")
        return

    # 2. KPIs Globais de Topo
    col1, col2, col3, col4 = st.columns(4)

    total_frotas = len(df_status)
    frotas_vermelho = int((df_status["Status"] == "Vermelho").sum())
    frotas_amarelo = int((df_status["Status"] == "Amarelo").sum())
    frotas_verde = int((df_status["Status"] == "Verde").sum())

    menor_saldo_global = float(df_status["Menor_Saldo"].min())
    frota_pior_saldo = df_status.loc[df_status["Menor_Saldo"].idxmin(), "Frota"]

    total_formar = 0
    if necessidades_est:
        total_formar = sum(e.formacao_estrategica_sugerida for e in necessidades_est)

    with col1:
        render_metric_card(
            titulo="Frotas Monitoradas",
            valor=f"{total_frotas}",
            subtitulo=f"🟢 {frotas_verde} Estáveis | 🟡 {frotas_amarelo} Alerta",
            cor_borda="#0056b3"
        )

    with col2:
        render_metric_card(
            titulo="Frotas com Déficit Crítico",
            valor=f"{frotas_vermelho}",
            subtitulo="Abaixo da margem operacional mínima",
            cor_borda="#dc3545" if frotas_vermelho > 0 else "#28a745"
        )

    with col3:
        render_metric_card(
            titulo="Maior Déficit Pontual",
            valor=f"{menor_saldo_global:+.1f}".replace(".", ","),
            subtitulo=f"Gargalo registrado na Frota {frota_pior_saldo}",
            cor_borda="#dc3545"
        )

    with col4:
        render_metric_card(
            titulo="Formação Estratégica Global",
            valor=f"{total_formar}",
            subtitulo="Head Count recomendado para formação",
            cor_borda="#fd7e14"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Informações consolidadas por frota
    resumo_formacao: Dict[str, List[str]] = {}
    funcao_critica_map: Dict[str, Dict[str, Any]] = {}

    for e in necessidades_est:
        fr = e.frota.upper()
        if fr not in resumo_formacao:
            resumo_formacao[fr] = []
        if e.formacao_estrategica_sugerida > 0:
            resumo_formacao[fr].append(f"Formar {e.formacao_estrategica_sugerida} {e.funcao}")

        # Identifica função de maior déficit pico/médio na frota
        if fr not in funcao_critica_map or e.deficit_pico > funcao_critica_map[fr]["pico"]:
            funcao_critica_map[fr] = {
                "funcao": e.funcao,
                "pico": e.deficit_pico,
                "media": e.deficit_medio,
                "sugerida": e.formacao_estrategica_sugerida,
                "meses_criticos": e.meses_criticos_count,
                "total_meses": e.total_meses
            }

    # 4. Grid de Cards Executivos (2 colunas)
    st.subheader("📋 Diagnóstico Executivo por Frota")

    frotas_lista = df_status["Frota"].tolist()
    cols_grid = st.columns(2)

    for idx, frota_nome in enumerate(frotas_lista):
        row_status = df_status[df_status["Frota"] == frota_nome].iloc[0]
        col_atual = cols_grid[idx % 2]

        crit_info = funcao_critica_map.get(frota_nome.upper(), {
            "funcao": "N/D",
            "pico": 0.0,
            "media": 0.0,
            "sugerida": 0,
            "meses_criticos": 0,
            "total_meses": row_status["Total_Meses_Projetados"]
        })

        acoes_frota = resumo_formacao.get(frota_nome.upper(), [])
        if acoes_frota:
            texto_recomendacao = "; ".join(acoes_frota)
        else:
            texto_recomendacao = "Quadro de instrutores equilibrado. Sem necessidade imediata de novas turmas."

        meses_crit_str = f"{crit_info['meses_criticos']} de {crit_info['total_meses']} meses"
        if row_status["Status"] == "Verde":
            meses_crit_str = "0 meses (Quadro suficiente)"

        with col_atual:
            render_card_frota_executiva(
                frota=frota_nome,
                status=row_status["Status"],
                menor_saldo=row_status["Menor_Saldo"],
                funcao_critica=f"{crit_info['funcao']} (Pico: {crit_info['pico']:.1f} | Média: {crit_info['media']:.1f})",
                meses_criticos=meses_crit_str,
                recomendacao=texto_recomendacao
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. Tabela Executiva Consolidada de Planejamento Estratégico
    st.subheader("🎯 Resumo Consolidado de Ações por Função")
    st.caption("Visão macro de todas as frotas com recomendações estratégicas calculadas sobre o horizonte móvel.")

    dados_tabela_macro = []
    for e in necessidades_est:
        dados_tabela_macro.append({
            "Frota": e.frota,
            "Função": e.funcao,
            "Déficit Pico": f"{e.deficit_pico:.1f}",
            "Déficit Médio Sustentado": f"{e.deficit_medio:.1f}",
            "Meses com Déficit": f"{e.meses_criticos_count} de {e.total_meses}",
            "Cobertura Cruzada Média (RN-12)": f"{e.cobertura_cruzada_media:.2f}",
            "Déficit Líquido": f"{e.deficit_liquido_estrategico:.2f}",
            "Formação Recomendada": f"Formar {e.formacao_estrategica_sugerida}" if e.formacao_estrategica_sugerida > 0 else "Quadro estável",
        })

    if dados_tabela_macro:
        df_macro = pd.DataFrame(dados_tabela_macro)
        st.dataframe(df_macro, use_container_width=True, hide_index=True)