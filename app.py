"""
SIPCAP - Sistema Inteligente de Planejamento de Capacidade de Instrutores.
Aplicação Web Streamlit (Azul Linhas Aéreas).
"""
import sys
from pathlib import Path
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engine.orchestrator import SIPCAPOrchestrator
from views.view_dashboard import render_view_dashboard
from views.view_necessidade_disponibilidade import render_view_necessidade_disponibilidade
from views.view_cobertura_cruzada import render_view_cobertura_cruzada
from views.view_plano_formacao import render_view_plano_formacao
from views.view_auditoria_calculo import render_view_auditoria_calculo
from views.view_consulta_operacional import render_view_consulta_operacional

# Configuração da Página
st.set_page_config(
    page_title="SIPCAP | Azul Linhas Aéreas",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Azul Linhas Aéreas
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #002244;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 0.9rem;
        color: #555;
        margin-bottom: 15px;
    }
    div[data-testid="stSidebarNav"] {
        display: none;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)


def obter_caminho_tabela(nome_base: str) -> Path:
    """Busca o arquivo de dados na pasta data/raw dando prioridade para .xlsx e fallback para .csv."""
    p_xlsx = ROOT_DIR / "data" / "raw" / f"{nome_base}.xlsx"
    if p_xlsx.exists():
        return p_xlsx
    p_csv = ROOT_DIR / "data" / "raw" / f"{nome_base}.csv"
    if p_csv.exists():
        return p_csv
    return p_xlsx


@st.cache_resource(show_spinner="Calculando capacidade e projeções analíticas...")
def carregar_orquestrador() -> SIPCAPOrchestrator:
    """Carrega dados brutos e executa o pipeline analítico completo do SIPCAP."""
    p_premissas = obter_caminho_tabela("tbl_premissas")
    p_simuladores = obter_caminho_tabela("tbl_simuladores")
    p_demanda = obter_caminho_tabela("tbl_demanda_slots")
    p_staffing = obter_caminho_tabela("tbl_crew_staffing")
    p_instrutores = obter_caminho_tabela("tbl_instrutores")

    orquestrador = SIPCAPOrchestrator.carregar_de_arquivos(
        p_premissas,
        p_simuladores,
        p_demanda,
        p_staffing,
        p_instrutores
    )
    orquestrador.executar()
    return orquestrador


def mudar_modulo_exec():
    """Callback para quando o usuário seleciona um item da Gestão Executiva."""
    if st.session_state.get("nav_exec"):
        st.session_state.pagina_selecionada = st.session_state.nav_exec
        st.session_state.nav_op = None


def mudar_modulo_op():
    """Callback para quando o usuário seleciona um item do Planejamento Operacional."""
    if st.session_state.get("nav_op"):
        st.session_state.pagina_selecionada = st.session_state.nav_op
        st.session_state.nav_exec = None


def render_sidebar(orquestrador: SIPCAPOrchestrator) -> str:
    """Renderiza menu lateral organizado por perfis de uso e metadados operacionais."""
    with st.sidebar:
        st.markdown("### ✈️ **SIPCAP**")
        st.caption("Planejamento de Capacidade • Azul")
        st.markdown("---")

        opcoes_exec = [
            "Tela 1 – Dashboard Executivo"
        ]

        opcoes_op = [
            "Tela 2 – Necessidade x Disponibilidade",
            "Tela 3 – Auditoria de Cálculo",
            "Tela 4 – Cobertura Cruzada (RN-12)",
            "Tela 5 – Plano Estratégico de Formação",
            "Tela 6 – Consulta Operacional"
        ]

        # Inicializa estado da navegação
        if "pagina_selecionada" not in st.session_state:
            st.session_state.pagina_selecionada = "Tela 1 – Dashboard Executivo"
            st.session_state.nav_exec = "Tela 1 – Dashboard Executivo"
            st.session_state.nav_op = None

        # 1. Bloco de Gestão Executiva
        st.markdown("#### 📊 **Gestão Executiva**")
        st.radio(
            "Módulo Executivo",
            options=opcoes_exec,
            key="nav_exec",
            on_change=mudar_modulo_exec,
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Bloco de Planejamento Operacional (Sequência lógica: 2 -> 3 -> 4 -> 5 -> 6)
        st.markdown("#### 📈 **Planejamento Operacional**")
        st.radio(
            "Módulo Operacional",
            options=opcoes_op,
            key="nav_op",
            on_change=mudar_modulo_op,
            label_visibility="collapsed"
        )

        pagina = st.session_state.pagina_selecionada

        # Metadados obtidos dos atributos reais do SIPCAPOrchestrator
        frotas_ativas = sorted(list({c.frota for c in orquestrador.calculos})) if orquestrador.calculos else sorted(list(orquestrador.simuladores.keys()))
        meses_unicos = sorted(list({c.mes_exibicao for c in orquestrador.calculos})) if orquestrador.calculos else sorted(list({d.mes for d in orquestrador.demanda_slots}))

        st.markdown("---")
        st.markdown("#### ⚙️ **Bases Carregadas**")
        st.caption(f"• Simuladores: {len(orquestrador.simuladores)} frotas")
        st.caption(f"• Instrutores: {len(orquestrador.instrutores)} ativos")
        st.caption(f"• Projeções Mensais: {len(meses_unicos)} meses")
        st.caption(f"• Frotas: {', '.join(frotas_ativas)}")

        if st.button("🔄 Recarregar Dados"):
            st.cache_resource.clear()
            st.rerun()

        st.markdown("---")
        st.caption("SIPCAP v3.1 • Fase 3")

    return pagina


def main():
    try:
        orquestrador = carregar_orquestrador()
    except Exception as e:
        st.error(f"Erro ao inicializar o motor analítico SIPCAP: {e}")
        st.exception(e)
        return

    tela_ativa = render_sidebar(orquestrador)

    # Sequência lógica estruturada e imune a variações de string
    if "Tela 1" in tela_ativa:
        render_view_dashboard(orquestrador)

    elif "Tela 2" in tela_ativa:
        render_view_necessidade_disponibilidade(orquestrador)

    elif "Tela 3" in tela_ativa:
        render_view_auditoria_calculo(orquestrador)

    elif "Tela 4" in tela_ativa:
        render_view_cobertura_cruzada(orquestrador)

    elif "Tela 5" in tela_ativa:
        render_view_plano_formacao(orquestrador)

    elif "Tela 6" in tela_ativa:
        render_view_consulta_operacional(orquestrador)


if __name__ == "__main__":
    main()