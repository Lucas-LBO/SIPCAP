"""
Componentes visuais de métricas, cards e semáforos RAG do SIPCAP.
"""
from typing import Optional
import streamlit as st


def render_rag_badge(status: str) -> str:
    """
    Retorna HTML formatado em linha única (sem quebras de linha ou indentação interna)
    de badge/etiqueta com a cor do status RAG.
    """
    st_norm = str(status).strip().capitalize()
    if st_norm == "Verde":
        bg_color = "#d4edda"
        text_color = "#155724"
        border_color = "#c3e6cb"
        icone = "🟢"
    elif st_norm == "Amarelo":
        bg_color = "#fff3cd"
        text_color = "#856404"
        border_color = "#ffeeba"
        icone = "🟡"
    else:  # Vermelho
        bg_color = "#f8d7da"
        text_color = "#721c24"
        border_color = "#f5c6cb"
        icone = "🔴"

    return (
        f'<span style="background-color: {bg_color}; color: {text_color}; '
        f'border: 1px solid {border_color}; padding: 3px 10px; border-radius: 12px; '
        f'font-weight: 600; font-size: 0.85rem; display: inline-block;">'
        f'{icone} {st_norm}</span>'
    )


def render_metric_card(
    titulo: str,
    valor: str | int | float,
    subtitulo: Optional[str] = None,
    delta: Optional[str] = None,
    cor_borda: str = "#003366"
) -> None:
    """
    Renderiza um card visual elegante para métricas de topo e KPIs executivos.
    Utiliza string HTML linearizada para garantir que o Markdown do Streamlit
    não interprete o recuo como bloco de código.
    """
    delta_html = ""
    if delta:
        delta_html = f"<div style='font-size: 0.85rem; color: #555; margin-top: 4px;'>{delta}</div>"

    sub_html = ""
    if subtitulo:
        sub_html = f"<div style='font-size: 0.8rem; color: #777; margin-top: 6px;'>{subtitulo}</div>"

    html = (
        f'<div style="background-color: #ffffff; border: 1px solid #e0e0e0; '
        f'border-left: 5px solid {cor_borda}; border-radius: 8px; padding: 16px 20px; '
        f'margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.04);">'
        f'<div style="font-size: 0.85rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">'
        f'{titulo}</div>'
        f'<div style="font-size: 1.8rem; font-weight: 700; color: #111; margin-top: 4px;">'
        f'{valor}</div>'
        f'{delta_html}{sub_html}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_card_frota_executiva(
    frota: str,
    status: str,
    menor_saldo: float,
    funcao_critica: str,
    meses_criticos: str,
    recomendacao: str
) -> None:
    """
    Renderiza o card executivo para a Tela 1 com resumo completo da frota.
    Utiliza string HTML linearizada sem indentação multiline para perfeita renderização no Streamlit.
    """
    st_norm = str(status).strip().capitalize()
    if st_norm == "Verde":
        cor_borda = "#28a745"
        cor_bg = "#f9fff9"
    elif st_norm == "Amarelo":
        cor_borda = "#ffc107"
        cor_bg = "#fffdf5"
    else:
        cor_borda = "#dc3545"
        cor_bg = "#fff8f8"

    badge = render_rag_badge(st_norm)
    saldo_str = f"{menor_saldo:+.2f}".replace(".", ",")
    cor_saldo = "#c82333" if menor_saldo < 0 else "#218838"

    html = (
        f'<div style="background-color: {cor_bg}; border: 1px solid #e5e5e5; '
        f'border-top: 4px solid {cor_borda}; border-radius: 8px; padding: 18px; '
        f'margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">'
        f'<h3 style="margin: 0; color: #002244; font-size: 1.3rem;">Frota {frota}</h3>'
        f'{badge}'
        f'</div>'
        f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem; margin-bottom: 12px;">'
        f'<div>'
        f'<span style="color: #666; font-size: 0.8rem;">MENOR SALDO:</span><br>'
        f'<strong style="color: {cor_saldo}; font-size: 1.1rem;">{saldo_str} Head Count</strong>'
        f'</div>'
        f'<div>'
        f'<span style="color: #666; font-size: 0.8rem;">MESES CRÍTICOS:</span><br>'
        f'<strong style="color: #333;">{meses_criticos}</strong>'
        f'</div>'
        f'</div>'
        f'<div style="font-size: 0.85rem; margin-bottom: 10px;">'
        f'<span style="color: #666;">FUNÇÃO MAIS CRÍTICA:</span><br>'
        f'<strong style="color: #003366;">{funcao_critica}</strong>'
        f'</div>'
        f'<div style="background-color: #ffffff; border-left: 3px solid #0056b3; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem; color: #222;">'
        f'🎯 <strong>Plano Estratégico:</strong> {recomendacao}'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)