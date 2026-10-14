"""
Tela 3 – Auditoria de Cálculo e Rastreabilidade do SIPCAP.

Refinamentos visuais aplicados:
1. Eliminação do texto com código hexadecimal nos cards superiores (uso estrito de cor_borda=).
2. Padronização numérica: Slots como inteiros sem decimais e Headcount (HC) com 2 casas decimais.
3. Padronização visual uniforme em toda a tela (Cards, Matriz e Memorial Matemático).
"""
import pandas as pd
import streamlit as st
from typing import Dict, Any

from components.cards import render_metric_card
from src.engine.orchestrator import SIPCAPOrchestrator


MAPA_METRICAS = {
    "Examinador Aeronauta": {
        "col_demanda": "Demanda_EX_Aeronauta",
        "col_hc_bruto": "HC_Bruto_EX_Aeronauta",
        "col_indisp_ferias": "Indisp_Ferias_EX_Aero",
        "col_indisp_trein": "Indisp_Trein_EX_Aero",
        "col_nec": "Necessidade_EX_Aeronauta",
        "col_disp": "Disponivel_EX_Aeronauta",
        "col_saldo": "Saldo_EX_Aeronauta",
        "col_rag": "RAG_EX_Aeronauta",
        "parceira": "Examinador Aeroviário",
        "col_saldo_parceira": "Saldo_EX_Aeroviario",
        "tipo_categoria": "Aeronauta"
    },
    "Examinador Aeroviário": {
        "col_demanda": "Demanda_EX_Aeroviario",
        "col_hc_bruto": "HC_Bruto_EX_Aeroviario",
        "col_indisp_ferias": "Indisp_Ferias_EX_Viario",
        "col_indisp_trein": "Indisp_Trein_EX_Viario",
        "col_nec": "Necessidade_EX_Aeroviario",
        "col_disp": "Disponivel_EX_Aeroviario",
        "col_saldo": "Saldo_EX_Aeroviario",
        "col_rag": "RAG_EX_Aeroviario",
        "parceira": "Examinador Aeronauta",
        "col_saldo_parceira": "Saldo_EX_Aeronauta",
        "tipo_categoria": "Aeroviario"
    },
    "Avaliador Aeronauta": {
        "col_demanda": "Demanda_AVA_Aeronauta",
        "col_hc_bruto": "HC_Bruto_AVA_Aeronauta",
        "col_indisp_ferias": "Indisp_Ferias_AVA_Aero",
        "col_indisp_trein": "Indisp_Trein_AVA_Aero",
        "col_nec": "Necessidade_AVA_Aeronauta",
        "col_disp": "Disponivel_AVA_Aeronauta",
        "col_saldo": "Saldo_AVA_Aeronauta",
        "col_rag": "RAG_AVA_Aeronauta",
        "parceira": "Avaliador Aeroviário",
        "col_saldo_parceira": "Saldo_AVA_Aeroviario",
        "tipo_categoria": "Aeronauta"
    },
    "Avaliador Aeroviário": {
        "col_demanda": "Demanda_AVA_Aeroviario",
        "col_hc_bruto": "HC_Bruto_AVA_Aeroviario",
        "col_indisp_ferias": "Indisp_Ferias_AVA_Viario",
        "col_indisp_trein": "Indisp_Trein_AVA_Viario",
        "col_nec": "Necessidade_AVA_Aeroviario",
        "col_disp": "Disponivel_AVA_Aeroviario",
        "col_saldo": "Saldo_AVA_Aeroviario",
        "col_rag": "RAG_AVA_Aeroviario",
        "parceira": "Avaliador Aeronauta",
        "col_saldo_parceira": "Saldo_AVA_Aeronauta",
        "tipo_categoria": "Aeroviario"
    }
}


def formatar_percentual(valor: Any) -> str:
    """Formata percentuais para até 2 casas decimais no padrão brasileiro."""
    try:
        val = float(valor)
        if val > 1.0:
            return f"{val:.2f}%".rstrip('0').rstrip('.').replace(".", ",") + "%" if val % 1 != 0 else f"{int(val)}%"
        else:
            p = val * 100.0
            return f"{p:.2f}%".rstrip('0').rstrip('.').replace(".", ",") + "%" if p % 1 != 0 else f"{int(p)}%"
    except (ValueError, TypeError):
        return str(valor)


def obter_premissas_relevantes(premissas: Any, funcao: str) -> Dict[str, Any]:
    """Premissas limpas e pertinentes ao recorte selecionado."""
    comuns = {
        "Indisp. Férias": formatar_percentual(getattr(premissas, 'FATOR_FERIAS_PERC', 0.0)),
        "Indisp. Treinamento": formatar_percentual(getattr(premissas, 'FATOR_TREINAMENTO_PERC', 0.0)),
        "Equivalência RN-12 (Aeroviário : Aeronauta)": f"1 : {getattr(premissas, 'CAPACIDADE_RATIO_AEROVIARIO', 2.0):.1f}"
    }

    if funcao == "Examinador Aeronauta":
        return {
            "Sessões / Mês": int(getattr(premissas, "SESSAO_EX_AERONAUTA", 0)),
            "Demanda da Função": formatar_percentual(getattr(premissas, 'PERC_EX_AERONAUTA', 0.0)),
            "Buffer Cheques": int(getattr(premissas, "BUFFER_CHEQUES", 0)),
            **comuns
        }
    elif funcao == "Examinador Aeroviário":
        return {
            "Sessões / Mês": int(getattr(premissas, "SESSAO_EX_AEROVIARIO", 0)),
            "Demanda da Função": formatar_percentual(getattr(premissas, 'PERC_EX_AEROVIARIO', 0.0)),
            "Buffer Cheques": int(getattr(premissas, "BUFFER_CHEQUES", 0)),
            **comuns
        }
    elif funcao == "Avaliador Aeronauta":
        return {
            "Sessões / Mês": int(getattr(premissas, "SESSAO_AVA_AERONAUTA", 0)),
            "Demanda da Função": formatar_percentual(getattr(premissas, 'PERC_AVA_AERONAUTA', 0.0)),
            "Lead Time Formação": f"{getattr(premissas, 'PRAZO_FORMACAO_AVALIADOR', 2)} meses",
            **comuns
        }
    else:  # Avaliador Aeroviário
        return {
            "Sessões / Mês": int(getattr(premissas, "SESSAO_AVA_AEROVIARIO", 0)),
            "Demanda da Função": formatar_percentual(getattr(premissas, 'PERC_AVA_AEROVIARIO', 0.0)),
            "PSM Aeroviário (Horas/Mês)": getattr(premissas, "PSM_AEROVIARIO", "-"),
            "Lead Time Formação": f"{getattr(premissas, 'PRAZO_FORMACAO_AVALIADOR', 2)} meses",
            **comuns
        }


def render_view_auditoria_calculo(orquestrador: SIPCAPOrchestrator) -> None:
    st.title("🔍 Auditoria de Cálculo & Rastreabilidade")
    st.markdown(
        "Ambiente técnico de validação e transparência operacional. "
        "Permite reconstruir e explicar cada indicador de necessidade, disponibilidade, saldo e aplicação da RN-12."
    )
    st.markdown("---")

    df_auditoria = orquestrador.dataframe_auditoria
    if df_auditoria.empty:
        st.warning("Não há base de auditoria processada no momento.")
        return

    premissas = orquestrador.premissas
    ratio_rn12 = getattr(premissas, "CAPACIDADE_RATIO_AEROVIARIO", 2.0)

    # 1. Filtros de Auditoria
    col_f1, col_f2, col_f3 = st.columns(3)
    frotas = sorted(df_auditoria["Frota"].unique().tolist())
    with col_f1:
        sel_frota = st.selectbox("Frota em Auditoria:", frotas, index=0)

    funcoes = list(MAPA_METRICAS.keys())
    with col_f2:
        sel_func = st.selectbox("Função Técnica em Auditoria:", funcoes, index=0)

    df_frota = df_auditoria[df_auditoria["Frota"] == sel_frota].copy()
    col_mes = "Mês" if "Mês" in df_frota.columns else "Mes"
    meses_disponiveis = ["Todos os Meses (Visão Geral)"] + df_frota[col_mes].tolist()
    with col_f3:
        sel_mes = st.selectbox("Recorte Temporal:", meses_disponiveis, index=0)

    cfg = MAPA_METRICAS[sel_func]

    # 2. Painel de Premissas Contextualizadas
    with st.expander(f"⚙️ Premissas Relevantes Aplicadas — {sel_func} ({sel_frota})", expanded=False):
        premissas_dict = obter_premissas_relevantes(premissas, sel_func)
        cols_p = st.columns(len(premissas_dict))
        for col, (label, val) in zip(cols_p, premissas_dict.items()):
            col.metric(label=label, value=str(val))

    # Construção dos Dados de Auditoria
    nome_col_parceira = f"Superávit Parceira ({cfg['parceira']})"
    linhas_tabela = []
    valores_numericos = []

    for _, row in df_frota.iterrows():
        mes_nome = row[col_mes]
        dem_cons = float(row.get("Demanda_Considerada", 0.0))
        dem_func = float(row.get(cfg["col_demanda"], 0.0))
        hc_bruto = float(row.get(cfg["col_hc_bruto"], 0.0))
        indisp_f = float(row.get(cfg["col_indisp_ferias"], 0.0))
        indisp_t = float(row.get(cfg["col_indisp_trein"], 0.0))
        nec = float(row.get(cfg["col_nec"], 0.0))
        disp = float(row.get(cfg["col_disp"], 0.0))
        saldo = float(row.get(cfg["col_saldo"], 0.0))
        rag = row.get(cfg["col_rag"], "Verde")

        # RN-12 Simultânea
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

        # Status estrito da cobertura
        if def_bruto <= 1e-6:
            status_cob = "Sem cobertura"
        elif cob_rn12 >= def_bruto - 1e-6:
            status_cob = "Cobertura integral"
        elif cob_rn12 > 1e-6:
            status_cob = "Cobertura parcial"
        else:
            status_cob = "Sem cobertura"

        # Guarda valores numéricos puros para os cards e o memorial matemático
        valores_numericos.append({
            "mes": mes_nome,
            "nec": nec,
            "disp": disp,
            "saldo": saldo,
            "def_liq": def_liq,
            "hc_bruto": hc_bruto,
            "indisp_f": indisp_f,
            "indisp_t": indisp_t,
            "sup_parc": sup_parc,
            "cob_rn12": cob_rn12,
            "status_cob": status_cob
        })

        # Linha formatada da tabela visual (inteiros para slots, 2 decimais para HC)
        linhas_tabela.append({
            "Mês": mes_nome,
            "Demanda Considerada (Slots)": int(round(dem_cons)),
            "Demanda Função (Slots)": int(round(dem_func)),
            "HC Bruto": f"{hc_bruto:.2f}",
            "Indisp. Férias (HC)": f"{indisp_f:.2f}",
            "Indisp. Trein. (HC)": f"{indisp_t:.2f}",
            "Necessidade Final (HC)": f"{nec:.2f}",
            "Disponibilidade (HC)": f"{disp:.2f}",
            "Saldo Operacional": f"{saldo:+.2f}",
            "RAG": rag,
            nome_col_parceira: f"{sup_parc:.2f}",
            "Cobertura RN-12 Aproveitada": f"{cob_rn12:.2f}",
            "Déficit Líquido": f"{def_liq:.2f}",
            "Status da Cobertura": status_cob
        })

    df_matriz = pd.DataFrame(linhas_tabela)
    df_nums = pd.DataFrame(valores_numericos)

    # 3. Métricas Resumo do Recorte (Cards sem texto de cor)
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    media_nec = df_nums["nec"].mean()
    media_disp = df_nums["disp"].mean()
    pior_saldo = df_nums["saldo"].min()
    med_liq = df_nums["def_liq"].sum() / len(df_nums)

    with c1:
        render_metric_card(
            titulo="Necessidade Média",
            valor=f"{media_nec:.2f}",
            subtitulo="Slots convertidos em HC",
            cor_borda="#0056b3"
        )
    with c2:
        render_metric_card(
            titulo="Disponibilidade Média",
            valor=f"{media_disp:.2f}",
            subtitulo="Quadro ativo na base",
            cor_borda="#28a745"
        )
    with c3:
        cor_s = "#dc3545" if pior_saldo < 0 else "#28a745"
        render_metric_card(
            titulo="Menor Saldo Bruto",
            valor=f"{pior_saldo:+.2f}",
            subtitulo="Pior gargalo pré-RN-12",
            cor_borda=cor_s
        )
    with c4:
        cor_l = "#fd7e14" if med_liq > 0 else "#28a745"
        render_metric_card(
            titulo="Média Líquida (12M)",
            valor=f"{med_liq:.2f}",
            subtitulo="Base de turmas da Tela 5",
            cor_borda=cor_l
        )

    # 4. Matriz de Rastreabilidade Ponta a Ponta com Destaque Visual RN-12
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📋 Matriz de Rastreabilidade Ponta a Ponta (Pipeline Mensal)")
    st.caption("Visão sequencial do dado bruto até o déficit líquido. As colunas em destaque azul integram a RN-12.")

    df_exibicao = df_matriz.copy()
    if sel_mes != "Todos os Meses (Visão Geral)":
        df_exibicao = df_exibicao[df_exibicao["Mês"] == sel_mes]

    colunas_destaque_rn12 = [
        nome_col_parceira,
        "Cobertura RN-12 Aproveitada",
        "Déficit Líquido",
        "Status da Cobertura"
    ]

    def style_rn12_columns(col):
        if col.name in colunas_destaque_rn12:
            return ['background-color: #f0f7fc; font-weight: 500; color: #0b3954;'] * len(col)
        return [''] * len(col)

    styled_df = df_exibicao.style.apply(style_rn12_columns, axis=0)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Botão de Exportação para Auditoria Externa
    csv_bytes = df_matriz.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Exportar Matriz Completa de Auditoria (CSV)",
        data=csv_bytes,
        file_name=f"auditoria_sipcap_{sel_frota}_{sel_func.replace(' ', '_')}.csv",
        mime="text/csv"
    )

    # 5. Dicionário de Linhagem & Origem dos Dados
    with st.expander("📌 Linhagem & Origem dos Dados (Mapeamento de Fontes)"):
        st.markdown("""
        | Coluna / Indicador | Tabela / Fonte de Origem | Regra de Negócio / Lógica de Transformação |
        | :--- | :--- | :--- |
        | **Demanda Considerada** | `tbl_simuladores` vs `tbl_projecoes` | `RN-02`: Limitação pelo gargalo físico do simulador (`min(Demanda, Capacidade)`). |
        | **Demanda Função** | `tbl_projecoes` + `PremissasModel` | Proporção de slots alocada à função conforme `% PERC_EX / PERC_AVA`. |
        | **HC Bruto** | Cálculo Motor | Divisão de slots pelo volume mensal de sessões do instrutor (`SESSAO_...`). |
        | **Indisp. Férias / Trein.** | `PremissasModel` | `RN-06/07`: Acréscimo de capacidade para ausências legais de escala. |
        | **Necessidade Final** | Motor de Capacidade | `HC Bruto + Indisp. Férias + Indisp. Treinamento`. |
        | **Disponibilidade** | `tbl_instrutores` | Contagem nominal dos profissionais ativos na base cadastrados para a frota. |
        | **Saldo Operacional** | Linha de Balanço | `Disponibilidade - Necessidade Final` (`RN-09`). |
        | **Superávit Parceira** | `tbl_instrutores` + `tbl_projecoes` | Saldo positivo da categoria parceira da mesma frota no mesmo mês. |
        | **Cobertura RN-12** | Motor Prescritivo | `RN-12`: Compensação simultânea (1 Aeroviário = 2 Aeronautas). |
        | **Déficit Líquido** | Balanço Final | Déficit remanescente não absorvido pela RN-12. Alimenta a Tela 5. |
        | **Status da Cobertura** | Classificação RN-12 | `Cobertura integral`, `Cobertura parcial` ou `Sem cobertura`. |
        """)

    # 6. Memorial Descritivo & Raio-X Matemático
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🧮 Memorial Descritivo & Raio-X Matemático")
    st.caption("Demonstração algébrica das equações resolvidas para o mês selecionado.")

    mes_alvo = df_frota[col_mes].iloc[0] if sel_mes == "Todos os Meses (Visão Geral)" else sel_mes
    row_num = df_nums[df_nums["mes"] == mes_alvo].iloc[0]

    with st.container():
        st.markdown(f"#### Memorial de Cálculo: **{sel_func}** | Frota **{sel_frota}** | Mês **{mes_alvo}**")

        st.markdown(f"""
        **Passo 1: Composição da Necessidade (HC)**
        $$\\text{{Necessidade Final}} = \\text{{HC Bruto}} + \\text{{Férias}} + \\text{{Treinamento}} = {row_num['hc_bruto']:.2f} + {row_num['indisp_f']:.2f} + {row_num['indisp_t']:.2f} = \\mathbf{{{row_num['nec']:.2f} \\text{{ HC}}}}$$

        **Passo 2: Apuração do Saldo Operacional Bruto**
        $$\\text{{Saldo Bruto}} = \\text{{Disponível}} - \\text{{Necessidade}} = {row_num['disp']:.2f} - {row_num['nec']:.2f} = \\mathbf{{{row_num['saldo']:+.2f} \\text{{ HC}}}}$$

        **Passo 3: Aplicação da Cobertura Cruzada Simultânea (RN-12)**
        * Déficit da Função em {mes_alvo}: `{abs(min(0.0, row_num['saldo'])):.2f} HC`
        * Superávit da Parceira ({cfg['parceira']}): `{row_num['sup_parc']:.2f} HC`
        * Capacidade de Absorção: `min(Déficit, Superávit × Equivalência) = {row_num['cob_rn12']:.2f} HC`
        * Status da Cobertura: **{row_num['status_cob']}**
        $$\\text{{Déficit Líquido}} = \\max(0, \\text{{Déficit Bruto}} - \\text{{Cobertura Aproveitada}}) = \\mathbf{{{row_num['def_liq']:.2f} \\text{{ HC}}}}$$

        **Passo 4: Impacto no Planejamento Estratégico Anual (Tela 5)**
        Este mês contribui com **{row_num['def_liq']:.2f} HC** para a soma dos 12 meses.
        A média sustentada anual da frota é calculada por:
        $$\\text{{Média Anual Sustentada}} = \\frac{{\\sum_{{m=1}}^{{12}} \\text{{Déficit Líquido}}_m}}{{12}} = \\frac{{{df_nums['def_liq'].sum():.2f}}}{{12}} = \\mathbf{{{med_liq:.2f} \\text{{ profissionais}}}}$$
        """)