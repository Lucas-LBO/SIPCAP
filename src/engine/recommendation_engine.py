"""
Motor de Recomendações e Cobertura Cruzada (RN-12) do SIPCAP.

Implementa:
- Diagnóstico de Cobertura Cruzada entre Aeronautas e Aeroviários com estrita simultaneidade mensal:
  1 Aeroviário = 2 Aeronautas (capacidade)
  1 Aeronauta = 0,5 Aeroviário (capacidade)
- Geração de recomendações prescritivas inteligentes:
  Identifica o mês crítico, frota, função afetada, quantidade necessária
  e calcula a data limite de disparo com base no PRAZO_FORMACAO_AVALIADOR.
- Abordagem de Examinadores:
  Como Examinadores provêm do quadro de Avaliadores, a recomendação orienta
  a promoção de Avaliadores e a formação preventiva de novos Avaliadores para reposição.
"""
import math
from typing import List, Dict, Tuple, Optional, Any
from ..domain.schemas import (
    CalculoMensalFrota,
    PremissasModel,
    CoberturaCruzadaResultado,
    RecomendacaoAcao
)
from ..utils.date_utils import (
    subtrair_meses,
    formatar_ano_mes_exibicao
)


class RecommendationEngine:
    """
    Motor prescritivo e de otimização operacional do SIPCAP.
    """

    @classmethod
    def analisar_cobertura_cruzada_funcao(
        cls,
        frota: str,
        ano_mes: str,
        mes_exibicao: str,
        funcao_grupo: str,  # 'Avaliador' ou 'Examinador'
        saldo_aeronauta: float,
        saldo_aeroviario: float,
        ratio_aeroviario: float = 2.0
    ) -> Optional[CoberturaCruzadaResultado]:
        """
        RN-12: Cobertura Cruzada entre Aeronautas e Aeroviários com estrita simultaneidade no mesmo mês.
        Retorna CoberturaCruzadaResultado se houver um polo deficitário e outro superavitário no mês.
        """
        # Caso 1: Aeronauta Deficitário e Aeroviário Superavitário no mesmo mês
        if saldo_aeronauta < -1e-6 and saldo_aeroviario > 1e-6:
            deficit_orig = abs(saldo_aeronauta)
            superavit = saldo_aeroviario
            # 1 Aeroviário = ratio Aeronautas (padrão 2.0)
            capacidade_cobertura = min(deficit_orig, superavit * ratio_aeroviario)

            if capacidade_cobertura >= deficit_orig - 1e-6:
                tipo = "Integral"
                pct = 100.0
                deficit_rem = 0.0
                msg = (
                    f"Superávit de {superavit:.1f} {funcao_grupo}(es) Aeroviário(s) "
                    f"cobre integralmente (100%) o déficit de {deficit_orig:.1f} Aeronauta(s) "
                    f"via Cobertura Cruzada (RN-12, razão 1:2)."
                )
            else:
                tipo = "Parcial"
                pct = (capacidade_cobertura / deficit_orig) * 100.0
                deficit_rem = deficit_orig - capacidade_cobertura
                msg = (
                    f"Superávit de {superavit:.1f} {funcao_grupo}(es) Aeroviário(s) "
                    f"absorve {capacidade_cobertura:.1f} do déficit ({pct:.1f}%). "
                    f"Déficit remanescente: {deficit_rem:.1f} {funcao_grupo}(es) Aeronauta(s)."
                )

            return CoberturaCruzadaResultado(
                frota=frota,
                ano_mes=ano_mes,
                mes_exibicao=mes_exibicao,
                funcao_deficitaria=f"{funcao_grupo} Aeronauta",
                funcao_superavitaria=f"{funcao_grupo} Aeroviario",
                deficit_original=round(deficit_orig, 2),
                superavit_disponivel=round(superavit, 2),
                capacidade_cobertura=round(capacidade_cobertura, 2),
                percentual_cobertura=round(pct, 1),
                tipo_cobertura=tipo,
                deficit_remanescente=round(deficit_rem, 2),
                mensagem_diagnostico=msg
            )

        # Caso 2: Aeroviário Deficitário e Aeronauta Superavitário no mesmo mês
        elif saldo_aeroviario < -1e-6 and saldo_aeronauta > 1e-6:
            deficit_orig = abs(saldo_aeroviario)
            superavit = saldo_aeronauta
            # 1 Aeronauta = 0.5 Aeroviário -> capacidade = superavit / ratio
            capacidade_cobertura = min(deficit_orig, superavit / ratio_aeroviario)

            if capacidade_cobertura >= deficit_orig - 1e-6:
                tipo = "Integral"
                pct = 100.0
                deficit_rem = 0.0
                msg = (
                    f"Superávit de {superavit:.1f} {funcao_grupo}(es) Aeronauta(s) "
                    f"cobre integralmente (100%) o déficit de {deficit_orig:.1f} Aeroviário(s) "
                    f"via Cobertura Cruzada (RN-12, razão 2:1)."
                )
            else:
                tipo = "Parcial"
                pct = (capacidade_cobertura / deficit_orig) * 100.0
                deficit_rem = deficit_orig - capacidade_cobertura
                msg = (
                    f"Superávit de {superavit:.1f} {funcao_grupo}(es) Aeronauta(s) "
                    f"absorve {capacidade_cobertura:.1f} do déficit ({pct:.1f}%). "
                    f"Déficit remanescente: {deficit_rem:.1f} {funcao_grupo}(es) Aeroviário(s)."
                )

            return CoberturaCruzadaResultado(
                frota=frota,
                ano_mes=ano_mes,
                mes_exibicao=mes_exibicao,
                funcao_deficitaria=f"{funcao_grupo} Aeroviario",
                funcao_superavitaria=f"{funcao_grupo} Aeronauta",
                deficit_original=round(deficit_orig, 2),
                superavit_disponivel=round(superavit, 2),
                capacidade_cobertura=round(capacidade_cobertura, 2),
                percentual_cobertura=round(pct, 1),
                tipo_cobertura=tipo,
                deficit_remanescente=round(deficit_rem, 2),
                mensagem_diagnostico=msg
            )

        return None

    @classmethod
    def gerar_recomendacoes_calculo(
        cls,
        calculo: CalculoMensalFrota,
        premissas: PremissasModel
    ) -> Tuple[List[CoberturaCruzadaResultado], List[RecomendacaoAcao]]:
        """
        Analisa um cálculo mensal e gera:
        1. Lista de diagnósticos de cobertura cruzada simultânea
        2. Lista de recomendações prescritivas
        """
        coberturas: List[CoberturaCruzadaResultado] = []
        recomendacoes: List[RecomendacaoAcao] = []

        ratio = premissas.CAPACIDADE_RATIO_AEROVIARIO
        prazo_formacao = premissas.PRAZO_FORMACAO_AVALIADOR
        mes_limite = subtrair_meses(calculo.ano_mes, prazo_formacao)
        mes_limite_exib = formatar_ano_mes_exibicao(mes_limite)

        # 1. Análise Cruzada Simultânea para Avaliadores
        cob_ava = cls.analisar_cobertura_cruzada_funcao(
            frota=calculo.frota,
            ano_mes=calculo.ano_mes,
            mes_exibicao=calculo.mes_exibicao,
            funcao_grupo="Avaliador",
            saldo_aeronauta=calculo.saldo_ava_aeronauta,
            saldo_aeroviario=calculo.saldo_ava_aeroviario,
            ratio_aeroviario=ratio
        )
        if cob_ava:
            coberturas.append(cob_ava)

        # 2. Análise Cruzada Simultânea para Examinadores
        cob_ex = cls.analisar_cobertura_cruzada_funcao(
            frota=calculo.frota,
            ano_mes=calculo.ano_mes,
            mes_exibicao=calculo.mes_exibicao,
            funcao_grupo="Examinador",
            saldo_aeronauta=calculo.saldo_ex_aeronauta,
            saldo_aeroviario=calculo.saldo_ex_aeroviario,
            ratio_aeroviario=ratio
        )
        if cob_ex:
            coberturas.append(cob_ex)

        # Mapeamento para emissão de recomendações operacionais
        funcoes = [
            ("Avaliador Aeronauta", calculo.saldo_ava_aeronauta, cob_ava),
            ("Avaliador Aeroviario", calculo.saldo_ava_aeroviario, cob_ava),
            ("Examinador Aeronauta", calculo.saldo_ex_aeronauta, cob_ex),
            ("Examinador Aeroviario", calculo.saldo_ex_aeroviario, cob_ex),
        ]

        for nome_funcao, saldo, cob_result in funcoes:
            if saldo < -1e-6:
                deficit_orig = abs(saldo)
                teve_cobertura = False
                deficit_rem = deficit_orig

                if cob_result and cob_result.funcao_deficitaria == nome_funcao:
                    teve_cobertura = True
                    deficit_rem = cob_result.deficit_remanescente

                # Se déficit remanescente for zero (cobertura integral), apenas registra informativo
                if deficit_rem <= 1e-6:
                    recomendacoes.append(
                        RecomendacaoAcao(
                            frota=calculo.frota,
                            ano_mes_evento=calculo.ano_mes,
                            mes_exibicao=calculo.mes_exibicao,
                            funcao=nome_funcao,
                            deficit_original=round(deficit_orig, 2),
                            cobertura_cruzada=True,
                            deficit_remanescente=0.0,
                            acao_recomendada=f"Déficit de {deficit_orig:.1f} coberto integralmente por Cobertura Cruzada (RN-12). Sem necessidade de turma.",
                            mes_limite_inicio=mes_limite,
                            mes_limite_exibicao=mes_limite_exib,
                            antecedencia_meses=prazo_formacao,
                            prioridade="Informativa"
                        )
                    )
                else:
                    qtd_formar = math.ceil(round(deficit_rem, 2))
                    prioridade = "Crítica" if deficit_rem >= 1.0 else "Moderada"

                    if "Examinador" in nome_funcao:
                        acao = (
                            f"Déficit remanescente de {deficit_rem:.1f} {nome_funcao}. "
                            f"Promover {qtd_formar} Avaliador(es) experiente(s) a Examinador "
                            f"e abrir turma de {qtd_formar} novo(s) Avaliador(es) para reposição da base até {mes_limite_exib}."
                        )
                    else:
                        acao = (
                            f"Déficit remanescente de {deficit_rem:.1f} {nome_funcao}. "
                            f"Abrir turma para formação de {qtd_formar} novo(s) {nome_funcao} com início limite em {mes_limite_exib} "
                            f"(lead time de {prazo_formacao} meses)."
                        )

                    recomendacoes.append(
                        RecomendacaoAcao(
                            frota=calculo.frota,
                            ano_mes_evento=calculo.ano_mes,
                            mes_exibicao=calculo.mes_exibicao,
                            funcao=nome_funcao,
                            deficit_original=round(deficit_orig, 2),
                            cobertura_cruzada=teve_cobertura,
                            deficit_remanescente=round(deficit_rem, 2),
                            acao_recomendada=acao,
                            mes_limite_inicio=mes_limite,
                            mes_limite_exibicao=mes_limite_exib,
                            antecedencia_meses=prazo_formacao,
                            prioridade=prioridade
                        )
                    )

        return coberturas, recomendacoes

    @classmethod
    def calcular_necessidade_estrategica_horizonte(
        cls,
        todos_calculos: List[CalculoMensalFrota],
        premissas: PremissasModel,
        janela_meses: int = 13
    ) -> List[Any]:
        """
        Calcula a necessidade sustentada em horizonte móvel deslizante (ex: 13 meses)
        com simultaneidade real mês a mês de Cobertura Cruzada (RN-12).
        """
        from ..domain.schemas import NecessidadeEstrategicaHorizonte
        import numpy as np

        resultados: List[NecessidadeEstrategicaHorizonte] = []
        if not todos_calculos:
            return resultados

        frotas = sorted(list({c.frota for c in todos_calculos}))
        ratio = premissas.CAPACIDADE_RATIO_AEROVIARIO

        funcoes_map = [
            ("Avaliador Aeronauta", "saldo_ava_aeronauta", "Avaliador", "Aeronauta"),
            ("Avaliador Aeroviario", "saldo_ava_aeroviario", "Avaliador", "Aeroviario"),
            ("Examinador Aeronauta", "saldo_ex_aeronauta", "Examinador", "Aeronauta"),
            ("Examinador Aeroviario", "saldo_ex_aeroviario", "Examinador", "Aeroviario"),
        ]

        for frota in frotas:
            calcs_frota = sorted([c for c in todos_calculos if c.frota == frota], key=lambda x: x.ano_mes)
            total_meses = len(calcs_frota)

            for i, c_atual in enumerate(calcs_frota):
                janela = calcs_frota[i : min(i + janela_meses, total_meses)]
                qtd_janela = len(janela)
                mes_ref = c_atual.ano_mes
                mes_fim = janela[-1].ano_mes
                rotulo_horizonte = f"{formatar_ano_mes_exibicao(mes_ref)} a {formatar_ano_mes_exibicao(mes_fim)} ({qtd_janela}M)"

                for nome_func, campo_saldo, grupo, cat in funcoes_map:
                    campo_parceiro = (
                        f"saldo_{'ava' if grupo == 'Avaliador' else 'ex'}_{'aeroviario' if cat == 'Aeronauta' else 'aeronauta'}"
                    )

                    deficits_brutos = []
                    coberturas_aproveitadas = []
                    deficits_liquidos = []

                    for c in janela:
                        s_foco = getattr(c, campo_saldo)
                        s_parceiro = getattr(c, campo_parceiro)

                        # 1. Déficit Bruto simultâneo
                        def_bruto = abs(s_foco) if s_foco < -1e-6 else 0.0

                        # 2. Superávit Parceiro simultâneo
                        sup_parceiro = s_parceiro if s_parceiro > 1e-6 else 0.0

                        # 3. Capacidade de Cobertura Simultânea
                        cob_mes = 0.0
                        if def_bruto > 1e-6 and sup_parceiro > 1e-6:
                            if cat == "Aeronauta":
                                cob_mes = min(def_bruto, sup_parceiro * ratio)
                            else:
                                cob_mes = min(def_bruto, sup_parceiro / ratio)

                        def_liq_mes = max(0.0, def_bruto - cob_mes)

                        deficits_brutos.append(def_bruto)
                        coberturas_aproveitadas.append(cob_mes)
                        deficits_liquidos.append(def_liq_mes)

                    pico = max(deficits_brutos) if deficits_brutos else 0.0
                    media_bruta = float(np.mean(deficits_brutos)) if deficits_brutos else 0.0
                    mediana_liquida = float(np.median(deficits_liquidos)) if deficits_liquidos else 0.0
                    meses_criticos = sum(1 for d in deficits_brutos if d > 1e-6)

                    if pico <= 1e-6:
                        continue  # Sem déficit no horizonte

                    cob_media = float(np.mean(coberturas_aproveitadas)) if coberturas_aproveitadas else 0.0
                    def_estrategico_rem = float(np.mean(deficits_liquidos)) if deficits_liquidos else 0.0
                    formacao_sugerida = math.ceil(round(def_estrategico_rem, 2))
                    tem_cob = cob_media > 1e-6

                    # Diagnóstico explicativo
                    if formacao_sugerida == 0 and tem_cob:
                        diag = (
                            f"Déficit médio de {media_bruta:.1f} profissionais em {rotulo_horizonte} "
                            f"está 100% mitigado via Cobertura Cruzada simultânea (RN-12). "
                            f"Não requer abertura de turmas fixas."
                        )
                    elif pico > formacao_sugerida:
                        pico_sobra = round(pico - formacao_sugerida, 1)
                        diag = (
                            f"Necessidade média sustentada de {def_estrategico_rem:.1f} profissionais no horizonte {rotulo_horizonte}. "
                            f"Recomendação Estratégica: Formar {formacao_sugerida} profissionais para evitar ociosidade pós-pico. "
                            f"O pico de {pico:.1f} (excedente pontual de {pico_sobra}) deve ser absorvido via gestão operacional/RN-12."
                        )
                    else:
                        diag = (
                            f"Necessidade estável no horizonte {rotulo_horizonte}. "
                            f"Recomendação Estratégica: Formar {formacao_sugerida} profissionais."
                        )

                    resultados.append(
                        NecessidadeEstrategicaHorizonte(
                            frota=frota,
                            mes_referencia=mes_ref,
                            horizonte_rotulo=rotulo_horizonte,
                            funcao=nome_func,
                            deficit_pico_operacional=round(pico, 2),
                            deficit_medio_sustentado=round(def_estrategico_rem, 2),
                            deficit_mediano=round(mediana_liquida, 2),
                            meses_criticos_count=meses_criticos,
                            total_meses_analisados=qtd_janela,
                            cobertura_cruzada_aplicavel=tem_cob,
                            capacidade_cobertura_cruzada=round(cob_media, 2),
                            deficit_estrategico_final=round(def_estrategico_rem, 2),
                            formacao_estrategica_sugerida=formacao_sugerida,
                            diagnostico_estrategico=diag
                        )
                    )

        return resultados

    @classmethod
    def calcular_necessidade_estrategica_consolidada(
        cls,
        todos_calculos: List[CalculoMensalFrota],
        premissas: PremissasModel
    ) -> Tuple[List[Any], List[Any]]:
        """
        Analisa todo o período disponível de planejamento (do início ao último mês)
        e gera UMA recomendação final única por (Frota, Função), com estrita simultaneidade mensal de Cobertura Cruzada (RN-12).

        Retorna:
        - List[NecessidadeEstrategicaConsolidada]: Tabela executiva com 1 linha por Frota e Função.
        - List[CoberturaCruzadaConsolidada]: Resumo executivo de RN-12 com Déficit Médio, Capacidade Média e Déficit Líquido.
        """
        from ..domain.schemas import NecessidadeEstrategicaConsolidada, CoberturaCruzadaConsolidada
        import numpy as np

        if not todos_calculos:
            return [], []

        frotas = sorted(list({c.frota for c in todos_calculos}))
        resultados_est: List[NecessidadeEstrategicaConsolidada] = []
        resultados_cob: List[CoberturaCruzadaConsolidada] = []

        funcoes_map = [
            ("Avaliador Aeronauta", "saldo_ava_aeronauta", "Avaliador", "Aeronauta"),
            ("Avaliador Aeroviario", "saldo_ava_aeroviario", "Avaliador", "Aeroviario"),
            ("Examinador Aeronauta", "saldo_ex_aeronauta", "Examinador", "Aeronauta"),
            ("Examinador Aeroviario", "saldo_ex_aeroviario", "Examinador", "Aeroviario"),
        ]

        ratio = premissas.CAPACIDADE_RATIO_AEROVIARIO

        for frota in frotas:
            calcs_frota = sorted([c for c in todos_calculos if c.frota == frota], key=lambda x: x.ano_mes)
            total_meses = len(calcs_frota)
            if total_meses == 0:
                continue

            mes_inicio_exib = calcs_frota[0].mes_exibicao
            mes_fim_exib = calcs_frota[-1].mes_exibicao
            rotulo_periodo = f"{mes_inicio_exib} a {mes_fim_exib} ({total_meses} meses)"

            for nome_func, campo_saldo, grupo, cat in funcoes_map:
                campo_parceiro = (
                    f"saldo_{'ava' if grupo == 'Avaliador' else 'ex'}_{'aeroviario' if cat == 'Aeronauta' else 'aeronauta'}"
                )

                deficits_brutos = []
                coberturas_aproveitadas = []
                deficits_liquidos = []

                # Cálculo com estrita simultaneidade mês a mês (RN-12)
                for c in calcs_frota:
                    s_foco = getattr(c, campo_saldo)
                    s_parceiro = getattr(c, campo_parceiro)

                    # 1. Déficit Bruto do mês
                    def_bruto = abs(s_foco) if s_foco < -1e-6 else 0.0

                    # 2. Superávit Disponível na Parceira no mesmo mês
                    sup_parceiro = s_parceiro if s_parceiro > 1e-6 else 0.0

                    # 3. Cobertura Simultânea aproveitada no mês
                    cob_mes = 0.0
                    if def_bruto > 1e-6 and sup_parceiro > 1e-6:
                        if cat == "Aeronauta":
                            # 1 Aeroviário supre até 2 Aeronautas (superavit * ratio)
                            cob_mes = min(def_bruto, sup_parceiro * ratio)
                        else:
                            # 1 Aeronauta supre até 0.5 Aeroviário (superavit / ratio)
                            cob_mes = min(def_bruto, sup_parceiro / ratio)

                    # 4. Déficit Líquido do mês
                    def_liq_mes = max(0.0, def_bruto - cob_mes)

                    deficits_brutos.append(def_bruto)
                    coberturas_aproveitadas.append(cob_mes)
                    deficits_liquidos.append(def_liq_mes)

                pico = max(deficits_brutos) if deficits_brutos else 0.0
                meses_criticos = sum(1 for d in deficits_brutos if d > 1e-6)

                # Médias divididas pelo total de meses analisados (planejamento anual sustentado)
                media_bruta = float(np.mean(deficits_brutos)) if deficits_brutos else 0.0
                cob_media = float(np.mean(coberturas_aproveitadas)) if coberturas_aproveitadas else 0.0
                deficit_liquido = float(np.mean(deficits_liquidos)) if deficits_liquidos else 0.0
                mediana_liquida = float(np.median(deficits_liquidos)) if deficits_liquidos else 0.0

                formacao_sugerida = math.ceil(round(deficit_liquido, 2))
                tem_cob = cob_media > 1e-6
                perc_cob = round((cob_media / media_bruta * 100.0) if media_bruta > 1e-6 else 0.0, 1)

                # Diagnósticos descritivos
                if pico <= 1e-6:
                    diag = f"Quadro equilibrado no período ({rotulo_periodo}). Sem déficit identificado."
                elif formacao_sugerida == 0 and tem_cob:
                    diag = (
                        f"Déficit médio de {media_bruta:.1f} em {rotulo_periodo} está 100% mitigado "
                        f"via Cobertura Cruzada simultânea (RN-12). Não requer formação fixa."
                    )
                elif pico > formacao_sugerida:
                    pico_sobra = round(pico - formacao_sugerida, 1)
                    diag = (
                        f"Necessidade média sustentada de {deficit_liquido:.1f} profissionais em {rotulo_periodo}. "
                        f"Recomendação Final: Formar {formacao_sugerida} profissionais. "
                        f"O excedente pontual de pico ({pico_sobra}) deve ser absorvido via gestão operacional/RN-12."
                    )
                else:
                    diag = (
                        f"Necessidade estável no período {rotulo_periodo}. "
                        f"Recomendação Final: Formar {formacao_sugerida} profissionais."
                    )

                diag_cob = (
                    f"A Cobertura Cruzada simultânea mitigou uma média de {cob_media:.2f} profissionais "
                    f"ao longo de {total_meses} meses ({perc_cob}% do déficit médio)."
                    if tem_cob
                    else "Sem simultaneidade de superávit na categoria parceira para cobertura cruzada."
                )

                resultados_est.append(
                    NecessidadeEstrategicaConsolidada(
                        frota=frota,
                        funcao=nome_func,
                        periodo_analisado=rotulo_periodo,
                        total_meses=total_meses,
                        deficit_pico=round(pico, 2),
                        deficit_medio=round(media_bruta, 2),
                        deficit_mediano=round(mediana_liquida, 2),
                        meses_criticos_count=meses_criticos,
                        cobertura_cruzada_media=round(cob_media, 2),
                        deficit_liquido_estrategico=round(deficit_liquido, 2),
                        formacao_estrategica_sugerida=formacao_sugerida,
                        diagnostico_estrategico=diag
                    )
                )

                resultados_cob.append(
                    CoberturaCruzadaConsolidada(
                        frota=frota,
                        funcao=nome_func,
                        periodo_analisado=rotulo_periodo,
                        total_meses=total_meses,
                        deficit_medio=round(media_bruta, 2),
                        capacidade_media_cobertura=round(cob_media, 2),
                        deficit_liquido_estrategico=round(deficit_liquido, 2),
                        percentual_cobertura_media=perc_cob,
                        diagnostico=diag_cob
                    )
                )

        return resultados_est, resultados_cob