"""
Tela 4 – Cobertura Cruzada (RN-12) do SIPCAP.

Objetivos:
- Apresentar o diagnóstico analítico de intercâmbio de capacidade conforme RN-12 com estrita simultaneidade mensal.
- Mostrar como o superávit simultâneo de uma categoria (Aeronauta ou Aeroviário) amortece carências da parceira na mesma frota e mês.
- Exibir a taxa de conversão parametrizável em Premissas (CAPACIDADE_RATIO_AEROVIARIO):
    1 Aeroviário = 2 Aeronautas (capacidade)
    1 Aeronauta = 0,5 Aeroviário (capacidade)
- Permitir filtros por Frota, Função e Tipo de Cobertura (Integral ou Parcial).
- Registrar a memória de cálculo para auditoria:
    Capacidade de Cobertura = min(Déficit Original, Superávit Parceiro × Ratio)
    Déficit Remanescente = Déficit Original - Capacidade de Cobertura
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from typing import List

from components.cards import render_metric_card
from src.engine.orchestrator import SIPCAPOrchestrator


def render_view_cobertura_cruzada(orquestrador: SIPCAPOrchestrator) -> None:
    st.title("🔄 Cobertura Cruzada (RN-12)")
    st.markdown(
        "Diagnóstico de aproveitamento de capacidade ociosa entre categorias técnicas (Aeronautas e Aeroviários) "
        "com **estrita simultaneidade mensal** dentro da mesma frota. "
        "A aplicação da RN-12 evita abertura desnecessária de turmas quando existe superávit qualificado no mesmo período."
    )
    st.markdown("---")

    coberturas_consolidadas = orquestrador.coberturas_cruzadas_consolidadas
    coberturas_mensais = orquestrador.coberturas_cruzadas
    ratio_ativo = orquestrador.premissas.CAPACIDADE_RATIO_AEROVIARIO

    # 1. Indicadores Globais de Topo
    col1, col2, col3, col4 = st.columns(4)

    total_eventos_cobertura = len(coberturas_mensais)
    coberturas_integrais = sum(1 for c in coberturas_mensais if c.tipo_cobertura == "Integral")
    coberturas_parciais = sum(1 for c in coberturas_mensais if c.tipo_cobertura == "Parcial")

    # Média de capacidade de cobertura entre todas as frotas
    media_absorvida = 0.0
    if coberturas_consolidadas:
        media_absorvida = sum(c.capacidade_media_cobertura for c in coberturas_consolidadas) / len(coberturas_consolidadas)

    with col1:
        render_metric_card(
            titulo="Ratio Parametrizado (RN-12)",
            valor=f"{ratio_ativo:.2f}",
            subtitulo="1 Aeroviário = 2 Aeronautas",
            cor_borda="#0056b3"
        )

    with col2:
        render_metric_card(
            titulo="Ocorrências Simultâneas",
            valor=f"{total_eventos_cobertura}",
            subtitulo="Meses com cobertura efetiva no mesmo período",
            cor_borda="#2a9d8f"
        )

    with col3:
        render_metric_card(
            titulo="Eficácia da Cobertura",
            valor=f"{coberturas_integrais} Integrais",
            subtitulo=f"e {coberturas_parciais} Parciais registradas",
            cor_borda="#28a745" if coberturas_integrais > 0 else "#ffc107"
        )

    with col4:
        render_metric_card(
            titulo="Amortecimento Médio Global",
            valor=f"{media_absorvida:.2f} HC",
            subtitulo="Redução média de déficit sustentado",
            cor_borda="#fd7e14"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Tabela Executiva Consolidada da RN-12
    st.subheader("🎯 Visão Consolidada no Horizonte por Frota e Função")
    st.caption("Efeito cumulativo da Cobertura Cruzada simultânea reduzindo a necessidade líquida de novas turmas.")

    dados_cons = []
    for c in coberturas_consolidadas:
        dados_cons.append({
            "Frota": getattr(c, "frota", ""),
            "Função": getattr(c, "funcao", ""),
            "Período de Planejamento": getattr(c, "periodo_analisado", ""),
            "Déficit Médio Original": f"{getattr(c, 'deficit_medio', 0.0):.2f}",
            "Capacidade Média de Cobertura": f"{getattr(c, 'capacidade_media_cobertura', 0.0):.2f}",
            "Déficit Líquido Estratégico": f"{getattr(c, 'deficit_liquido_estrategico', 0.0):.2f}",
            "Cobertura Média (%)": f"{getattr(c, 'percentual_cobertura_media', 0.0):.1f}%",
            "Diagnóstico": getattr(c, "diagnostico", "")
        })

    if dados_cons:
        df_c = pd.DataFrame(dados_cons)
        st.dataframe(df_c, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma oportunidade de cobertura cruzada registrada nas premissas vigentes.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Detalhamento Mensal com Filtros Operacionais
    st.subheader("📋 Detalhamento Mensal de Intercâmbio de Capacidade")
    st.caption("Eventos mensais onde ocorreu simultaneidade de déficit em uma categoria e superávit na parceira.")

    dados_mensais = []
    for m in coberturas_mensais:
        dados_mensais.append({
            "Frota": getattr(m, "frota", ""),
            "Ano_Mes": getattr(m, "ano_mes", ""),
            "Mês": getattr(m, "mes_exibicao", ""),
            "Função Deficitária": getattr(m, "funcao_deficitaria", ""),
            "Função Superavitária": getattr(m, "funcao_superavitaria", ""),
            "Déficit Original (HC)": getattr(m, "deficit_original", 0.0),
            "Superávit Disponível (HC)": getattr(m, "superavit_disponivel", 0.0),
            "Capacidade Cobertura (HC)": getattr(m, "capacidade_cobertura", 0.0),
            "Cobertura (%)": f"{getattr(m, 'percentual_cobertura', 0.0):.1f}%",
            "Tipo Cobertura": getattr(m, "tipo_cobertura", ""),
            "Déficit Remanescente (HC)": getattr(m, "deficit_remanescente", 0.0),
            "Diagnóstico": getattr(m, "mensagem_diagnostico", "")
        })

    if dados_mensais:
        df_m = pd.DataFrame(dados_mensais)

        col_f1, col_f2 = st.columns(2)
        frotas_cob = ["Todas"] + sorted(df_m["Frota"].unique().tolist())
        tipos_cob = ["Todos"] + sorted(df_m["Tipo Cobertura"].unique().tolist())

        with col_f1:
            filtro_frota = st.selectbox("Filtrar Frota:", frotas_cob, index=0)
        with col_f2:
            filtro_tipo = st.selectbox("Filtrar Tipo de Cobertura:", tipos_cob, index=0)

        df_m_filtrado = df_m.copy()
        if filtro_frota != "Todas":
            df_m_filtrado = df_m_filtrado[df_m_filtrado["Frota"] == filtro_frota]
        if filtro_tipo != "Todos":
            df_m_filtrado = df_m_filtrado[df_m_filtrado["Tipo Cobertura"] == filtro_tipo]

        # Gráfico comparativo de déficit original vs remanescente
        if not df_m_filtrado.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_m_filtrado["Mês"] + " (" + df_m_filtrado["Frota"] + ")",
                y=df_m_filtrado["Déficit Original (HC)"],
                name="Déficit Original",
                marker_color="#e63946"
            ))
            fig.add_trace(go.Bar(
                x=df_m_filtrado["Mês"] + " (" + df_m_filtrado["Frota"] + ")",
                y=df_m_filtrado["Déficit Remanescente (HC)"],
                name="Déficit Após Cobertura RN-12",
                marker_color="#2a9d8f"
            ))
            fig.update_layout(
                barmode="group",
                height=380,
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Período e Frota",
                yaxis_title="Headcount Necessário",
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df_m_filtrado.drop(columns=["Ano_Mes"]), use_container_width=True, hide_index=True)
    else:
        st.info("Não foram identificados meses com simultaneidade de superávit de uma categoria e déficit de outra na mesma frota.")

    # 4. Memória de Cálculo Auditável
    with st.expander("ℹ️ Regras de Auditoria da RN-12 (Simultaneidade Operacional)"):
        st.markdown(f"""
        - **Estrita Simultaneidade**: A cobertura só ocorre se no **mesmo mês e mesma frota** uma categoria tiver carência (`Saldo < 0`) e a parceira tiver folga (`Saldo > 0`).
        - **Equivalência Técnica**:
            - 1 Aeroviário = `{ratio_ativo}` Aeronautas (`Capacidade = min(Déficit, Superávit × {ratio_ativo})`).
            - 1 Aeronauta = `{1.0/ratio_ativo:.1f}` Aeroviário (`Capacidade = min(Déficit, Superávit / {ratio_ativo})`).
        - **Déficit Líquido Mensal**: `max(0, Déficit Original - Capacidade de Cobertura)`.
        - **Planejamento Anual Sustentado**: O Déficit Líquido Estratégico anual é a média dos déficits líquidos mensais dividida pelo total de meses analisados ($N = 12$).
        """)