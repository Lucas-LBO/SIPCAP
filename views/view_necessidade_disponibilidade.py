"""
Tela 2 – Necessidade x Disponibilidade do SIPCAP.

Objetivos:
- Apresentar a dinâmica temporal mês a mês entre Necessidade, Disponibilidade e Saldo.
- Permitir filtros por Frota, Função (Examinador/Avaliador Aeronauta/Aeroviário) e Ano.
- Exibir indicadores de síntese, gráficos temporais comparativos e tabela com memória analítica.
- Registrar a memória de cálculo do saldo operacional (Saldo = Disponibilidade - Necessidade).
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from typing import List

from components.cards import render_metric_card
from src.engine.orchestrator import SIPCAPOrchestrator


MAPEAMENTO_FUNCOES = {
    "Examinador Aeronauta": {
        "col_nec": "Necessidade_EX_Aeronauta",
        "col_disp": "Disponivel_EX_Aeronauta",
        "col_saldo": "Saldo_EX_Aeronauta",
        "col_rag": "RAG_EX_Aeronauta"
    },
    "Examinador Aeroviário": {
        "col_nec": "Necessidade_EX_Aeroviario",
        "col_disp": "Disponivel_EX_Aeroviario",
        "col_saldo": "Saldo_EX_Aeroviario",
        "col_rag": "RAG_EX_Aeroviario"
    },
    "Avaliador Aeronauta": {
        "col_nec": "Necessidade_AVA_Aeronauta",
        "col_disp": "Disponivel_AVA_Aeronauta",
        "col_saldo": "Saldo_AVA_Aeronauta",
        "col_rag": "RAG_AVA_Aeronauta"
    },
    "Avaliador Aeroviário": {
        "col_nec": "Necessidade_AVA_Aeroviario",
        "col_disp": "Disponivel_AVA_Aeroviario",
        "col_saldo": "Saldo_AVA_Aeroviario",
        "col_rag": "RAG_AVA_Aeroviario"
    }
}


def render_view_necessidade_disponibilidade(orquestrador: SIPCAPOrchestrator) -> None:
    st.title("📈 Necessidade x Disponibilidade")
    st.markdown(
        "Acompanhamento da projeção de capacidade por frota e função operacional mês a mês. "
        "Permite identificar os meses exatos de déficit e o tamanho da folga ou falta de instrutores."
    )
    st.markdown("---")

    df_auditoria = orquestrador.dataframe_auditoria
    if df_auditoria.empty:
        st.warning("Não há dados de capacidade processados.")
        return

    # Garante coluna de Ano para filtro
    df = df_auditoria.copy()
    df["Ano"] = df["Ano_Mes"].apply(lambda x: str(x).split("-")[0])

    # 1. Filtros Superiores
    col_f1, col_f2, col_f3 = st.columns(3)

    frotas_disponiveis = sorted(df["Frota"].unique().tolist())
    with col_f1:
        frota_selecionada = st.selectbox("Frota:", frotas_disponiveis, index=0)

    funcoes_disponiveis = list(MAPEAMENTO_FUNCOES.keys())
    with col_f2:
        funcao_selecionada = st.selectbox("Função Técnica:", funcoes_disponiveis, index=0)

    anos_disponiveis = ["Todos"] + sorted(df["Ano"].unique().tolist())
    with col_f3:
        ano_selecionado = st.selectbox("Ano de Referência:", anos_disponiveis, index=0)

    # Aplicação dos filtros
    df_filtrado = df[df["Frota"] == frota_selecionada]
    if ano_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Ano"] == ano_selecionado]

    # Ordenação cronológica por Ano_Mes
    df_filtrado = df_filtrado.sort_values("Ano_Mes").reset_index(drop=True)

    if df_filtrado.empty:
        st.warning("Nenhum registro encontrado para o filtro selecionado.")
        return

    info_func = MAPEAMENTO_FUNCOES[funcao_selecionada]
    col_nec = info_func["col_nec"]
    col_disp = info_func["col_disp"]
    col_saldo = info_func["col_saldo"]
    col_rag = info_func["col_rag"]

    # 2. Métricas de Síntese
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    media_nec = df_filtrado[col_nec].mean()
    media_disp = df_filtrado[col_disp].mean()
    menor_saldo = df_filtrado[col_saldo].min()
    meses_deficit = int((df_filtrado[col_saldo] < 0).sum())
    total_meses = len(df_filtrado)

    with col_m1:
        render_metric_card(
            titulo="Necessidade Média",
            valor=f"{media_nec:.1f}",
            subtitulo=f"Slots / Horas convertidos em HC",
            cor_borda="#0056b3"
        )

    with col_m2:
        render_metric_card(
            titulo="Disponibilidade Média",
            valor=f"{media_disp:.1f}",
            subtitulo=f"Instrutores ativos no período",
            cor_borda="#28a745"
        )

    with col_m3:
        cor_saldo = "#dc3545" if menor_saldo < 0 else "#28a745"
        render_metric_card(
            titulo="Menor Saldo Pontual",
            valor=f"{menor_saldo:+.2f}".replace(".", ","),
            subtitulo="Pior gargalo identificado no recorte",
            cor_borda=cor_saldo
        )

    with col_m4:
        cor_crit = "#dc3545" if meses_deficit > 0 else "#28a745"
        render_metric_card(
            titulo="Meses com Déficit",
            valor=f"{meses_deficit} de {total_meses}",
            subtitulo="Períodos em que Saldo < 0",
            cor_borda=cor_crit
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Gráfico Interativo com Plotly
    st.subheader(f"📊 Evolução Temporal: {funcao_selecionada} (Frota {frota_selecionada})")

    fig = go.Figure()

    # Barra: Necessidade
    fig.add_trace(go.Bar(
        x=df_filtrado["Mês"],
        y=df_filtrado[col_nec],
        name="Necessidade (Headcount)",
        marker_color="#457b9d",
        opacity=0.85
    ))

    # Barra: Disponibilidade
    fig.add_trace(go.Bar(
        x=df_filtrado["Mês"],
        y=df_filtrado[col_disp],
        name="Disponibilidade Real",
        marker_color="#2a9d8f",
        opacity=0.85
    ))

    # Linha: Saldo
    fig.add_trace(go.Scatter(
        x=df_filtrado["Mês"],
        y=df_filtrado[col_saldo],
        name="Saldo Operacional",
        mode="lines+markers+text",
        text=[f"{v:+.1f}".replace(".", ",") for v in df_filtrado[col_saldo]],
        textposition="top center",
        line=dict(color="#e63946", width=3),
        marker=dict(size=8, color="#e63946")
    ))

    # Linha de referência no zero
    fig.add_hline(y=0, line_dash="dash", line_color="#333", annotation_text="Ponto de Equilíbrio (0)")

    fig.update_layout(
        barmode="group",
        height=450,
        margin=dict(l=20, r=20, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Mês Projetado",
        yaxis_title="Profissionais (Headcount)",
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 4. Tabela Mensal com Destaques
    st.subheader("📋 Memória Mensal de Cálculo")
    st.caption("Visão detalhada mês a mês calculada pelo motor de capacidade.")

    col_cap_sim = "Capacidade_Simulador" if "Capacidade_Simulador" in df_filtrado.columns else "Capacidade_Simulador_Total"
    cap_sim_valores = df_filtrado[col_cap_sim] if col_cap_sim in df_filtrado.columns else "-"

    df_tabela = pd.DataFrame({
        "Mês": df_filtrado["Mês"],
        "Capacidade Simulador (slots)": cap_sim_valores,
        "Demanda Considerada (slots)": df_filtrado["Demanda_Considerada"],
        "Necessidade (HC)": df_filtrado[col_nec].round(2),
        "Disponibilidade (HC)": df_filtrado[col_disp],
        "Saldo Operacional (HC)": df_filtrado[col_saldo].round(2),
        "Semáforo RAG": df_filtrado[col_rag]
    })

    st.dataframe(df_tabela, use_container_width=True, hide_index=True)

    # 5. Nota Explicativa das Regras de Negócio
    with st.expander("ℹ️ Regras de Negócio e Fórmula do Cálculo (RN-01 a RN-11)"):
        st.markdown("""
        - **Capacidade Simulador (slots)**: Calculada por `Dias do Mês × Slots/Dia × Dispositivos`.
        - **Demanda Considerada**: Se a Demanda Real for menor que a capacidade do simulador, o simulador dita o gargalo físico mínimo de operação.
        - **Necessidade (HC)**: `(Demanda em Slots × Ratio de Execução / Capacidade Mês do Instrutor) × Fatores de Indisponibilidade (Férias + Treinamento Próprio)`.
        - **Disponibilidade (HC)**: Contagem dos profissionais ativos na base `tbl_instrutores` cadastrados para a respectiva frota e função.
        - **Saldo Operacional**: `Disponibilidade - Necessidade`. Quando negativo, indica carência e aciona a RN-12 (Cobertura Cruzada) ou RN-13 (Formação).
        """)