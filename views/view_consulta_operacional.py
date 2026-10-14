"""
Tela 6 – Centro de Consulta Operacional do SIPCAP (Versão Final Homologada).

Refinamentos finais aplicados:
1. Ordenação cronológica estrita (Jan → Dez) garantida por Ano_Mes em gráficos, tabelas e filtros.
2. Destaque visual nas métricas e colunas da RN-12 (ícones, badges e estilização com cor institucional).
3. Card do Pior Mês enriquecido: exibe simultaneamente Déficit Bruto, Cobertura RN-12 e Déficit Líquido.
4. Tabela analítica padronizada (inteiros e HC com até 2 casas) com realce visual nas colunas da RN-12.
5. Preservação integral das regras de cálculo e arquitetura pronta para Copiloto.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any, List

from components.cards import render_metric_card
from src.engine.orchestrator import SIPCAPOrchestrator


MAPA_FUNCOES_CONSULTA = {
    "Examinador Aeronauta": {
        "col_nec": "Necessidade_EX_Aeronauta",
        "col_disp": "Disponivel_EX_Aeronauta",
        "col_saldo": "Saldo_EX_Aeronauta",
        "col_rag": "RAG_EX_Aeronauta",
        "parceira": "Examinador Aeroviário",
        "col_saldo_parceira": "Saldo_EX_Aeroviario",
        "tipo_categoria": "Aeronauta"
    },
    "Examinador Aeroviário": {
        "col_nec": "Necessidade_EX_Aeroviario",
        "col_disp": "Disponivel_EX_Aeroviario",
        "col_saldo": "Saldo_EX_Aeroviario",
        "col_rag": "RAG_EX_Aeroviario",
        "parceira": "Examinador Aeronauta",
        "col_saldo_parceira": "Saldo_EX_Aeronauta",
        "tipo_categoria": "Aeroviario"
    },
    "Avaliador Aeronauta": {
        "col_nec": "Necessidade_AVA_Aeronauta",
        "col_disp": "Disponivel_AVA_Aeronauta",
        "col_saldo": "Saldo_AVA_Aeronauta",
        "col_rag": "RAG_AVA_Aeronauta",
        "parceira": "Avaliador Aeroviário",
        "col_saldo_parceira": "Saldo_AVA_Aeroviario",
        "tipo_categoria": "Aeronauta"
    },
    "Avaliador Aeroviário": {
        "col_nec": "Necessidade_AVA_Aeroviario",
        "col_disp": "Disponivel_AVA_Aeroviario",
        "col_saldo": "Saldo_AVA_Aeroviario",
        "col_rag": "RAG_AVA_Aeroviario",
        "parceira": "Avaliador Aeronauta",
        "col_saldo_parceira": "Saldo_AVA_Aeronauta",
        "tipo_categoria": "Aeroviario"
    }
}


def extrair_base_operacional(df_auditoria: pd.DataFrame, ratio_rn12: float) -> pd.DataFrame:
    """Consolida os registros mensais ordenados cronologicamente com cálculo simultâneo da RN-12."""
    col_mes = "Mês" if "Mês" in df_auditoria.columns else "Mes"
    col_ano_mes = "Ano_Mes" if "Ano_Mes" in df_auditoria.columns else ("Ano_M" if "Ano_M" in df_auditoria.columns else col_mes)

    # Ordena cronologicamente pela chave Ano_Mes antes de extrair
    df_auditoria_ordenada = df_auditoria.sort_values(col_ano_mes).reset_index(drop=True)

    linhas = []
    for _, row in df_auditoria_ordenada.iterrows():
        frota = row["Frota"]
        mes = row[col_mes]
        ano_mes_val = str(row[col_ano_mes])
        ano = ano_mes_val.split("-")[0] if "-" in ano_mes_val else "2027"

        for nome_func, cfg in MAPA_FUNCOES_CONSULTA.items():
            nec = float(row.get(cfg["col_nec"], 0.0))
            disp = float(row.get(cfg["col_disp"], 0.0))
            saldo = float(row.get(cfg["col_saldo"], 0.0))
            rag = row.get(cfg["col_rag"], "Verde")

            saldo_parc = float(row.get(cfg["col_saldo_parceira"], 0.0))
            def_bruto = abs(saldo) if saldo < -1e-6 else 0.0
            sup_parc = saldo_parc if saldo_parc > 1e-6 else 0.0

            cob_rn12 = 0.0
            if def_bruto > 1e-6 and sup_parc > 1e-6:
                if cfg["tipo_categoria"] == "Aeronauta":
                    cob_rn12 = min(def_bruto, sup_parc * ratio_rn12)
                else:
                    cob_rn12 = min(def_bruto, sup_parc / ratio_rn12)

            def_liq = max(0.0, def_bruto - cob_rn12)

            linhas.append({
                "Frota": frota,
                "Função": nome_func,
                "Ano": ano,
                "Mês": mes,
                "Ano_Mes": ano_mes_val,
                "Necessidade": nec,
                "Disponibilidade": disp,
                "Saldo": saldo,
                "Déficit_Bruto": def_bruto,
                "Cobertura_RN12": cob_rn12,
                "Déficit_Líquido": def_liq,
                "RAG": rag
            })

    df = pd.DataFrame(linhas)
    return df.sort_values(["Ano_Mes", "Frota", "Função"]).reset_index(drop=True)


def extrair_payload_copiloto(df_recorte: pd.DataFrame, kpis: Dict[str, Any], insights: Dict[str, str]) -> Dict[str, Any]:
    """Empacota os dados do recorte atual em formato estruturado para o Copiloto SIPCAP."""
    return {
        "contexto_consulta": {
            "total_registros": len(df_recorte),
            "frotas_envolvidas": df_recorte["Frota"].unique().tolist(),
            "funcoes_envolvidas": df_recorte["Função"].unique().tolist(),
            "meses_analisados": df_recorte["Mês"].unique().tolist()
        },
        "kpis_resumo": kpis,
        "insights_operacionais": insights
    }


def render_view_consulta_operacional(orquestrador: SIPCAPOrchestrator) -> None:
    st.title("📋 Centro de Consulta Operacional")
    st.markdown(
        "Ambiente unificado para exploração livre de capacidade, diagnóstico rápido e "
        "análise de cenários operacionais por frota, função e período."
    )
    st.markdown("---")

    df_auditoria = orquestrador.dataframe_auditoria
    if df_auditoria.empty:
        st.warning("Não há dados de capacidade processados no momento.")
        return

    premissas = orquestrador.premissas
    ratio_rn12 = getattr(premissas, "CAPACIDADE_RATIO_AEROVIARIO", 2.0)

    # 1. Base consolidada completa com ordenação cronológica
    df_base = extrair_base_operacional(df_auditoria, ratio_rn12)

    # 2. Barra de Filtros Dinâmicos
    c_f1, c_f2, c_f3, c_f4 = st.columns(4)

    frotas_opcoes = ["Todas"] + sorted(df_base["Frota"].unique().tolist())
    with c_f1:
        sel_frota = st.selectbox("Frota:", frotas_opcoes, index=0)

    funcoes_opcoes = ["Todas"] + sorted(df_base["Função"].unique().tolist())
    with c_f2:
        sel_func = st.selectbox("Função Técnica:", funcoes_opcoes, index=0)

    anos_opcoes = ["Todos"] + sorted(df_base["Ano"].unique().tolist())
    with c_f3:
        sel_ano = st.selectbox("Ano:", anos_opcoes, index=0)

    # Ordenação cronológica estrita no dropdown de meses
    meses_cronologicos = df_base.sort_values("Ano_Mes")["Mês"].unique().tolist()
    meses_opcoes = ["Todos"] + meses_cronologicos
    with c_f4:
        sel_mes = st.selectbox("Mês:", meses_opcoes, index=0)

    # Aplicação dos Filtros
    df_recorte = df_base.copy()
    if sel_frota != "Todas":
        df_recorte = df_recorte[df_recorte["Frota"] == sel_frota]
    if sel_func != "Todas":
        df_recorte = df_recorte[df_recorte["Função"] == sel_func]
    if sel_ano != "Todos":
        df_recorte = df_recorte[df_recorte["Ano"] == sel_ano]
    if sel_mes != "Todos":
        df_recorte = df_recorte[df_recorte["Mês"] == sel_mes]

    if df_recorte.empty:
        st.warning("Nenhum dado encontrado para o recorte selecionado.")
        return

    # Garante ordenação cronológica para o recorte
    df_recorte = df_recorte.sort_values("Ano_Mes").reset_index(drop=True)

    # 3. Métricas de Síntese
    total_linhas = len(df_recorte)
    nec_media = df_recorte["Necessidade"].mean()
    disp_media = df_recorte["Disponibilidade"].mean()
    def_bruto_medio = df_recorte["Déficit_Bruto"].mean()
    def_liq_medio = df_recorte["Déficit_Líquido"].mean()
    cob_media = df_recorte["Cobertura_RN12"].mean()

    # Efetividade da Cobertura Cruzada (RN-12)
    soma_bruto = df_recorte["Déficit_Bruto"].sum()
    soma_cob = df_recorte["Cobertura_RN12"].sum()
    taxa_absorcao = (soma_cob / soma_bruto * 100.0) if soma_bruto > 1e-6 else 0.0

    meses_criticos_count = (df_recorte["Saldo"] < -1e-6).sum()

    # Pior Mês (Gargalo Nominal Completo: Bruto, RN-12 e Líquido)
    idx_pior = df_recorte["Saldo"].idxmin()
    pior_registro = df_recorte.loc[idx_pior]
    if pior_registro["Saldo"] < -1e-6:
        pior_mes_rotulo = pior_registro["Mês"]
        pior_subtitulo = (
            f"Bruto: {pior_registro['Déficit_Bruto']:.2f} | "
            f"RN-12: -{pior_registro['Cobertura_RN12']:.2f} | "
            f"Líq: {pior_registro['Déficit_Líquido']:.2f} HC"
        )
    else:
        pior_mes_rotulo = "Equilibrado"
        pior_subtitulo = "Sem déficits registrados no período"

    # Frotas e Funções mais críticas (visão agregada)
    frota_mais_critica = "-"
    func_mais_critica = "-"
    if sel_frota == "Todas":
        agg_frota = df_recorte.groupby("Frota")["Déficit_Líquido"].sum()
        if agg_frota.max() > 0:
            frota_mais_critica = f"{agg_frota.idxmax()} ({agg_frota.max():.1f} HC líq)"
    if sel_func == "Todas":
        agg_func = df_recorte.groupby("Função")["Déficit_Líquido"].sum()
        if agg_func.max() > 0:
            func_mais_critica = f"{agg_func.idxmax()} ({agg_func.max():.1f} HC líq)"

    # 4. Exibição dos KPIs de Topo
    st.subheader("📊 Resumo Operacional do Recorte")

    # Linha 1: Balanço Médio & Destaque RN-12
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_metric_card("Necessidade Média", f"{nec_media:.2f}", "Slots convertidos em HC", cor_borda="#0056b3")
    with k2:
        render_metric_card("Disponibilidade Média", f"{disp_media:.2f}", "Quadro ativo no período", cor_borda="#28a745")
    with k3:
        render_metric_card("Déficit Médio Bruto", f"{def_bruto_medio:.2f}", "Carência antes da RN-12", cor_borda="#dc3545")
    with k4:
        # Destaque Visual da Efetividade da RN-12
        render_metric_card(
            titulo="🔄 Absorção RN-12",
            valor=f"{taxa_absorcao:.1f}%",
            subtitulo=f"{cob_media:.2f} HC mitigados em média",
            cor_borda="#0077b6"
        )
    with k5:
        # Destaque Visual do Déficit Líquido Sustentado
        cor_l = "#fd7e14" if def_liq_medio > 0 else "#28a745"
        render_metric_card(
            titulo="🎯 Déficit Líquido",
            valor=f"{def_liq_medio:.2f}",
            subtitulo="Necessidade sustentada pós-RN-12",
            cor_borda=cor_l
        )

    # Linha 2: Criticidade, Pior Mês e Visão Global
    tem_vis_global = (sel_frota == "Todas" or sel_func == "Todas")
    num_cols_l2 = 4 if tem_vis_global else 2
    cols_l2 = st.columns(num_cols_l2)

    with cols_l2[0]:
        cor_crit = "#dc3545" if meses_criticos_count > 0 else "#28a745"
        render_metric_card("Meses Críticos", f"{meses_criticos_count} de {total_linhas}", "Ocorrências de Saldo < 0", cor_borda=cor_crit)
    with cols_l2[1]:
        # Pior Mês Enriquecido (Bruto, RN-12 e Líquido)
        render_metric_card(
            titulo="Pior Mês (Gargalo)",
            valor=pior_mes_rotulo,
            subtitulo=pior_subtitulo,
            cor_borda="#dc3545" if pior_registro["Saldo"] < -1e-6 else "#28a745"
        )

    if tem_vis_global:
        with cols_l2[2]:
            render_metric_card("Frota Mais Crítica", frota_mais_critica, "Maior carência líquida", cor_borda="#fd7e14")
        with cols_l2[3]:
            render_metric_card("Função Mais Crítica", func_mais_critica, "Cadeira sob maior pressão", cor_borda="#e63946")

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. Painel de Insights Acionáveis (Sem excesso de texto)
    st.subheader("💡 Insights Operacionais Acionáveis")

    # Diagnósticos Diretos
    if def_liq_medio <= 1e-6 and def_bruto_medio <= 1e-6:
        conclusao = "Operação equilibrada: o quadro ativo cobre integralmente a demanda do período sem necessidade de formação."
    elif def_liq_medio <= 1e-6 and def_bruto_medio > 1e-6:
        conclusao = "Déficit 100% mitigado: a Cobertura Cruzada da RN-12 eliminou integralmente a carência bruta."
    else:
        conclusao = f"Pressão sustentada: déficit líquido remanescente médio de {def_liq_medio:.2f} HC mesmo após a RN-12."

    if meses_criticos_count == 0:
        insight_meses = "Nenhum período de carência identificado no recorte."
    else:
        insight_meses = f"{meses_criticos_count} mês(es) com déficit, tendo o gargalo mais severo em {pior_mes_rotulo} ({pior_subtitulo})."

    if taxa_absorcao > 0:
        insight_rn12 = f"A RN-12 mitigou {taxa_absorcao:.1f}% da carência total, aliviando {cob_media:.2f} HC/mês via categoria parceira."
    else:
        insight_rn12 = "Sem efeito de Cobertura Cruzada: inexistência de superávit na parceira no mesmo mês/frota."

    if def_liq_medio > 0:
        recom_op = f"Adotar turmas conforme Tela 5 para carência sustentada ({def_liq_medio:.2f} HC); picos sazonais devem ser absorvidos na escala."
    else:
        recom_op = "Quadro estável. Não requer abertura de novas turmas de formação."

    insights_dict = {
        "conclusao_geral": conclusao,
        "meses_criticidade": insight_meses,
        "impacto_rn12": insight_rn12,
        "recomendacao_operacional": recom_op
    }

    ic1, ic2 = st.columns(2)
    with ic1:
        st.info(f"📌 **Conclusão Geral:** {conclusao}")
        st.warning(f"⚠️ **Meses Críticos:** {insight_meses}")
    with ic2:
        st.success(f"🔄 **Impacto RN-12:** {insight_rn12}")
        st.info(f"🎯 **Ação Recomendada:** {recom_op}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. Histórico Mensal Consolidado com Ordenação Cronológica Rígida (Gráfico + Tabela)
    st.subheader("📈 Evolução Temporal & Balanço Operacional")

    # Agregação cronológica por Ano_Mes para garantir Jan → Dez
    df_grafico = (
        df_recorte.groupby(["Ano_Mes", "Mês"], as_index=False)[["Necessidade", "Disponibilidade", "Saldo", "Cobertura_RN12", "Déficit_Líquido"]]
        .sum()
        .sort_values("Ano_Mes")
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_grafico["Mês"],
        y=df_grafico["Necessidade"],
        name="Necessidade (HC)",
        marker_color="#457b9d",
        opacity=0.85
    ))
    fig.add_trace(go.Bar(
        x=df_grafico["Mês"],
        y=df_grafico["Disponibilidade"],
        name="Disponibilidade Real",
        marker_color="#2a9d8f",
        opacity=0.85
    ))
    fig.add_trace(go.Scatter(
        x=df_grafico["Mês"],
        y=df_grafico["Saldo"],
        name="Saldo Bruto",
        mode="lines+markers",
        line=dict(color="#e63946", width=2.5),
        marker=dict(size=7)
    ))
    # Destaque para Déficit Líquido Pós-RN12
    fig.add_trace(go.Scatter(
        x=df_grafico["Mês"],
        y=-df_grafico["Déficit_Líquido"],
        name="Déficit Líquido (pós-RN12)",
        mode="lines+markers",
        line=dict(color="#fd7e14", width=3, dash="dash"),
        marker=dict(size=8, symbol="diamond")
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#333", annotation_text="Ponto de Equilíbrio (0)")

    fig.update_layout(
        barmode="group",
        height=420,
        margin=dict(l=20, r=20, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Mês Projetado (Ordem Cronológica)",
        yaxis_title="Headcount (HC)",
        xaxis=dict(categoryorder="array", categoryarray=df_grafico["Mês"].tolist()),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 7. Tabela Analítica do Recorte com Destaque nas Colunas RN-12
    st.subheader("📋 Tabela Analítica do Recorte")

    df_tabela_formatada = pd.DataFrame({
        "Mês": df_recorte["Mês"],
        "Frota": df_recorte["Frota"],
        "Função": df_recorte["Função"],
        "Necessidade": df_recorte["Necessidade"].apply(lambda x: f"{x:.2f}"),
        "Disponibilidade": df_recorte["Disponibilidade"].apply(lambda x: f"{x:.2f}"),
        "Saldo": df_recorte["Saldo"].apply(lambda x: f"{x:+.2f}"),
        "🔄 Cobertura RN-12": df_recorte["Cobertura_RN12"].apply(lambda x: f"{x:.2f}"),
        "🎯 Déficit Líquido": df_recorte["Déficit_Líquido"].apply(lambda x: f"{x:.2f}"),
        "Semáforo RAG": df_recorte["RAG"]
    })

    # Destaque visual azul institucional nas colunas da RN-12
    cols_destaque = ["🔄 Cobertura RN-12", "🎯 Déficit Líquido"]
    styled_tabela = df_tabela_formatada.style.apply(
        lambda col: ['background-color: #f0f7fc; font-weight: 600; color: #0b3954;'] * len(col) if col.name in cols_destaque else [''] * len(col),
        axis=0
    )
    st.dataframe(styled_tabela, use_container_width=True, hide_index=True)

    # Download CSV
    csv_bytes = df_recorte.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Exportar Dados Operacionais (CSV)",
        data=csv_bytes,
        file_name=f"consulta_operacional_sipcap_{sel_frota}_{sel_func.replace(' ', '_')}.csv",
        mime="text/csv"
    )

    # 8. Camada de Contexto para Copiloto / IA
    kpis_copiloto = {
        "necessidade_media": round(nec_media, 2),
        "disponibilidade_media": round(disp_media, 2),
        "deficit_medio_bruto": round(def_bruto_medio, 2),
        "absorcao_rn12_pct": round(taxa_absorcao, 1),
        "cobertura_media_hc": round(cob_media, 2),
        "deficit_liquido_medio": round(def_liq_medio, 2),
        "meses_criticos": f"{meses_criticos_count}/{total_linhas}",
        "pior_mes": pior_mes_rotulo,
        "detalhe_pior_mes": pior_subtitulo
    }
    st.session_state["copiloto_contexto_ativo"] = extrair_payload_copiloto(df_recorte, kpis_copiloto, insights_dict)