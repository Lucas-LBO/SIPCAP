"""
Tela 5 – Plano Estratégico de Formação do SIPCAP.

Objetivos:
- Apresentar a recomendação final estruturada de formação baseada no conceito de Horizonte Móvel e Déficit Sustentado (RN-13).
- Evitar superdimensionamento de turmas decorrente de picos isolados (compara Déficit Pico vs Déficit Médio vs Déficit Mediano).
- Incorporar o amortecimento gerado pela Cobertura Cruzada (RN-12).
- Gerar recomendação prescritiva única por Frota e Função.
- Apresentar visão temporal móvel e cronograma sugerido com lead time de formação.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from typing import List

from components.cards import render_metric_card
from src.engine.orchestrator import SIPCAPOrchestrator


def render_view_plano_formacao(orquestrador: SIPCAPOrchestrator) -> None:
    st.title("🎯 Plano Estratégico de Formação")
    st.markdown(
        "Dimensionamento inteligente de novas turmas de formação de Avaliadores e Examinadores. "
        "A metodologia do SIPCAP utiliza horizonte móvel e déficit médio sustentado para evitar a criação "
        "excessiva de turmas motivada por picos sazonais passageiros."
    )
    st.markdown("---")

    necessidades_consolidadas = orquestrador.necessidades_estrategicas_consolidadas
    
    premissas = orquestrador.premissas
    prazo_ava = premissas.PRAZO_FORMACAO_AVALIADOR
    prazo_ex = getattr(premissas, "PRAZO_FORMACAO_EXAMINADOR", getattr(premissas, "OFFSET_CHEQUE_MOVIMENTACAO", 3))

    # 1. KPIs Globais de Topo
    col1, col2, col3, col4 = st.columns(4)

    total_formar = sum(n.formacao_estrategica_sugerida for n in necessidades_consolidadas)
    frotas_com_turmas = len(set(n.frota for n in necessidades_consolidadas if n.formacao_estrategica_sugerida > 0))
    funcoes_impactadas = len([n for n in necessidades_consolidadas if n.formacao_estrategica_sugerida > 0])
    pico_maximo = max([n.deficit_pico for n in necessidades_consolidadas], default=0.0)

    with col1:
        render_metric_card(
            titulo="Total a Formar (Global)",
            valor=f"{total_formar}",
            subtitulo="Novos profissionais sustentados",
            cor_borda="#0056b3"
        )

    with col2:
        render_metric_card(
            titulo="Frotas Demandantes",
            valor=f"{frotas_com_turmas}",
            subtitulo="Requerem abertura de formação",
            cor_borda="#fd7e14" if frotas_com_turmas > 0 else "#28a745"
        )

    with col3:
        render_metric_card(
            titulo="Especialidades Impactadas",
            valor=f"{funcoes_impactadas}",
            subtitulo="Cadeiras técnicas em déficit",
            cor_borda="#2a9d8f"
        )

    with col4:
        render_metric_card(
            titulo="Maior Pico Isolado",
            valor=f"{pico_maximo:.1f} HC",
            subtitulo="Amortecido pela média móvel",
            cor_borda="#dc3545"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Tabela de Recomendação Final Estratégica (1 por Frota e Função)
    st.subheader("📋 Matriz Consolidada de Recomendações Estratégicas")
    st.caption("Síntese oficial para aprovação executiva da diretoria de operações de voo.")

    dados_plano = []
    for n in necessidades_consolidadas:
        prazo_aplicavel = prazo_ex if "Examinador" in n.funcao else prazo_ava
        dados_plano.append({
            "Frota": n.frota,
            "Função Técnica": n.funcao,
            "Período Analisado": n.periodo_analisado,
            "Déficit Pico (Gargalo)": f"{n.deficit_pico:.1f}",
            "Déficit Médio Sustentado": f"{n.deficit_medio:.1f}",
            "Meses com Déficit": f"{n.meses_criticos_count} de {n.total_meses}",
            "Cobertura RN-12 Média": f"{n.cobertura_cruzada_media:.2f}",
            "Déficit Líquido": f"{n.deficit_liquido_estrategico:.2f}",
            "Recomendação Final": f"Formar {n.formacao_estrategica_sugerida}" if n.formacao_estrategica_sugerida > 0 else "Quadro estável",
            "Lead Time Sugerido": f"{prazo_aplicavel} meses antes",
            "Diagnóstico Prescritivo": n.diagnostico_estrategico
        })

    df_plano = pd.DataFrame(dados_plano)

    # Filtros para exploração
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        frotas_filtro = ["Todas"] + sorted(df_plano["Frota"].unique().tolist())
        sel_frota = st.selectbox("Filtrar Frota:", frotas_filtro, index=0)
    with col_f2:
        funcoes_filtro = ["Todas"] + sorted(df_plano["Função Técnica"].unique().tolist())
        sel_func = st.selectbox("Filtrar Função:", funcoes_filtro, index=0)

    df_exibicao = df_plano.copy()
    if sel_frota != "Todas":
        df_exibicao = df_exibicao[df_exibicao["Frota"] == sel_frota]
    if sel_func != "Todas":
        df_exibicao = df_exibicao[df_exibicao["Função Técnica"] == sel_func]

    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Gráfico Comparativo: Pico vs Sustentado vs Recomendação
    st.subheader("📊 Comparativo Metodológico: Pico vs Médio Sustentado vs Turmas Recomendadas")
    st.caption("Demonstração visual do benefício da RN-13 evitando a superformação desnecessária.")

    df_grafico = df_exibicao.copy()
    df_grafico["pico_num"] = df_grafico["Déficit Pico (Gargalo)"].astype(float)
    df_grafico["medio_num"] = df_grafico["Déficit Médio Sustentado"].astype(float)
    df_grafico["formar_num"] = df_grafico["Recomendação Final"].apply(
        lambda x: int(x.replace("Formar ", "")) if "Formar" in x else 0
    )
    df_grafico["rotulo"] = df_grafico["Frota"] + " - " + df_grafico["Função Técnica"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_grafico["rotulo"],
        y=df_grafico["pico_num"],
        name="Déficit de Pico Isolado",
        marker_color="#e63946",
        opacity=0.7
    ))
    fig.add_trace(go.Bar(
        x=df_grafico["rotulo"],
        y=df_grafico["medio_num"],
        name="Déficit Médio Sustentado",
        marker_color="#457b9d",
        opacity=0.85
    ))
    fig.add_trace(go.Bar(
        x=df_grafico["rotulo"],
        y=df_grafico["formar_num"],
        name="Formação Recomendada (Final)",
        marker_color="#2a9d8f"
    ))

    fig.update_layout(
        barmode="group",
        height=450,
        margin=dict(l=20, r=20, t=30, b=120),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(tickangle=-45),
        yaxis_title="Quantidade de Profissionais",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 4. Memória de Cálculo Auditável
    with st.expander("ℹ️ Metodologia e Regras de Negócio do Dimensionamento Sustentado (RN-13)"):
        st.markdown(f"""
        - **Horizonte Móvel**: O cálculo avalia janelas consecutivas de até 13 meses sobre a demanda de simulador e chegadas do staffing.
        - **Déficit Sustentado vs Pico**: Se o déficit ocorrer em apenas 1 ou 2 meses isolados, a formação considera prioritariamente o déficit médio anual, amortecendo picos pontuais.
        - **Efeito da Cobertura Cruzada (RN-12)**: Antes de recomendar nova turma, o motor abate a capacidade de cobertura média cedida por instrutores superavitários.
        - **Lead Time Pré-operacional**:
            - Avaliador: `{prazo_ava}` meses de antecedência.
            - Examinador: `{prazo_ex}` meses de antecedência.
        """)