"""
Motor de cálculo de renda fixa — v1.5
Lógica core migrada do protótipo browser para Python.
Cada função é testável independentemente.
"""
from dataclasses import dataclass
from typing import Optional
import numpy_financial as npf

ISENTOS  = {"lci", "lca", "debi", "cri", "cra"}
FIDCS    = {"fidc_sr", "fidc_mz", "fidc_jr"}
IPCA_IDX = {"ipca_sp"}


@dataclass
class DadosMercado:
    selic:  float   # % a.a. — Meta Selic (COPOM)
    cdi:    float   # % a.a. — ≈ Selic − 0,10%
    ipca:   float   # % a.a. — IPCA acumulado 12 meses
    iproj:  float   # % a.a. — IPCA projetado Focus


@dataclass
class ResultadoAtivo:
    bruto:            float
    ir:               float
    liquido:          float
    juro_real:        float
    vol:              float
    sharpe:           float
    adequacao:        str    # ok | warn | no
    motivo:           str
    equiv_cdi_pct:    float  # % CDI equivalente líquido
    equiv_ipca_sp:    float  # spread IPCA+ equivalente (= juro real)
    benchmark_sharpe: float  # benchmark usado no cálculo do Sharpe


def get_ir(prazo_dias: int, isento: bool) -> float:
    """Tabela regressiva vigente (MP 1.303/2025 derrubada out/2025)."""
    if isento:          return 0.0
    if prazo_dias <= 180: return 0.225
    if prazo_dias <= 360: return 0.20
    if prazo_dias <= 720: return 0.175
    return 0.15


def calc_bruto(indexador: str, taxa: float, cdi: float, ipca: float) -> float:
    """Taxa bruta anual conforme indexador."""
    if indexador == "cdi_pct": return cdi * (taxa / 100)
    if indexador == "cdi_sp":  return cdi + taxa
    if indexador == "ipca_sp": return ipca + taxa
    return taxa  # prefixado


def calc_real(indexador: str, bruto: float, liquido: float,
              iproj: float, ipca_realizado: float = 0.0) -> float:
    """
    Juro real líquido.
    IPCA+spread: spread já É juro real — o título foi emitido com spread sobre IPCA.
      Usa ipca_realizado como base do spread (é sobre o que foi negociado).
      Aplica IR apenas sobre o spread bruto.
    Demais: taxa líquida − IPCA projetado.
    """
    if indexador in IPCA_IDX:
        # spread_bruto = taxa negociada sobre IPCA (base do título)
        spread_bruto = bruto - ipca_realizado
        ir_rate = (bruto - liquido) / bruto if bruto > 0 else 0
        return spread_bruto * (1 - ir_rate)
    return liquido - iproj


def get_vol(tipo: str, indexador: str, prazo_dias: int) -> float:
    """
    Volatilidade estimada por tipo de ativo.
    RF não tem vol histórica de preços — estimamos por duration e spread de crédito.
    """
    anos     = prazo_dias / 365
    duration = anos * 0.85
    if tipo == "fidc_sr": return 1.5
    if tipo == "fidc_mz": return 4.0
    if tipo == "fidc_jr": return 8.0
    if indexador in IPCA_IDX: return max(0.3, duration * 1.5)
    if indexador == "pre":    return max(0.5, duration * 2.5)
    return 0.3 if prazo_dias <= 365 else 0.5


def calc_sharpe(
    indexador: str, real: float, liquido: float,
    vol: float, mkt: DadosMercado
) -> tuple[float, float]:
    """
    Sharpe simplificado de RF com benchmark correto por base.
    IPCA+spread → base real (benchmark = CDI líq. real).
    Demais      → base nominal (benchmark = CDI líq. nominal).
    Retorna (sharpe, benchmark_usado).
    """
    cdi_liq_nominal = mkt.cdi * (1 - 0.15)
    cdi_liq_real    = cdi_liq_nominal - mkt.iproj
    if vol <= 0:
        return 0.0, cdi_liq_nominal
    if indexador in IPCA_IDX:
        return (real - cdi_liq_real) / vol, cdi_liq_real
    return (liquido - cdi_liq_nominal) / vol, cdi_liq_nominal


# ── Regras de adequação por perfil ──────────────────────────────────────────

PERFIL_REGRAS: dict = {
    "conservador": {
        "max_prazo": 730, "fgc_ob": True,
        "ok":   {"cdb", "lci", "lca", "tselic"},
        "warn": {"lc", "cri", "cra", "tipca", "tpre"},
        "no":   {"deb", "debi", "fidc_sr", "fidc_mz", "fidc_jr"},
    },
    "moderado": {
        "max_prazo": 1825, "fgc_ob": False,
        "ok":   {"cdb", "lci", "lca", "lc", "tselic", "tipca", "cri", "cra", "fidc_sr"},
        "warn": {"tpre", "debi", "fidc_mz"},
        "no":   {"deb", "fidc_jr"},
    },
    "sofisticado": {
        "max_prazo": 99999, "fgc_ob": False,
        "ok":   {"cdb","lci","lca","lc","tselic","tipca","tpre",
                 "deb","debi","cri","cra","fidc_sr","fidc_mz","fidc_jr"},
        "warn": set(), "no": set(),
    },
}


def avaliar_ativo(
    tipo: str, indexador: str, taxa: float,
    prazo_dias: int, fgc: bool, perfil: str,
    mkt: DadosMercado
) -> ResultadoAtivo:
    """Avalia um ativo completo — cálculo + adequação + equivalências."""
    isento  = tipo in ISENTOS
    ir      = get_ir(prazo_dias, isento)
    bruto   = calc_bruto(indexador, taxa, mkt.cdi, mkt.ipca)
    liquido = bruto * (1 - ir)
    real    = calc_real(indexador, bruto, liquido, mkt.iproj, mkt.ipca)
    vol     = get_vol(tipo, indexador, prazo_dias)
    sharpe, bench = calc_sharpe(indexador, real, liquido, vol, mkt)

    P = PERFIL_REGRAS.get(perfil, PERFIL_REGRAS["moderado"])
    adequacao, motivo = "ok", ""
    if tipo in P["no"]:
        adequacao, motivo = "no", "Produto não elegível para este perfil"
    elif prazo_dias > P["max_prazo"]:
        adequacao, motivo = "warn", "Prazo excede limite do perfil"
    elif P["fgc_ob"] and not fgc:
        adequacao, motivo = "warn", "FGC obrigatório para este perfil"
    elif tipo in P["warn"]:
        adequacao, motivo = "warn", "Elegível com atenção"

    return ResultadoAtivo(
        bruto=round(bruto, 4),
        ir=round(ir, 4),
        liquido=round(liquido, 4),
        juro_real=round(real, 4),
        vol=round(vol, 4),
        sharpe=round(sharpe, 4),
        adequacao=adequacao,
        motivo=motivo,
        equiv_cdi_pct=round((liquido / mkt.cdi * 100) if mkt.cdi > 0 else 0, 2),
        equiv_ipca_sp=round(real, 4),
        benchmark_sharpe=round(bench, 4),
    )


def tir_bullet(taxa_liquida_aa: float, prazo_dias: int, valor: float = 1000.0) -> float:
    """
    TIR para título bullet (pagamento único no vencimento).
    Para títulos com cupons, usar tir_com_cupons() — v2.0.
    """
    anos = prazo_dias / 365
    vf = valor * ((1 + taxa_liquida_aa / 100) ** anos)
    tir = npf.irr([-valor, vf])
    return round(tir * 100, 4)


def marktomarket(
    taxa_compra: float, taxa_mercado: float,
    prazo_total_anos: float, tempo_decorrido_anos: float,
    valor: float = 1000.0
) -> dict:
    """
    Estimativa de mark-to-market por variação de taxa.
    Preço MTM = VF descontado pela taxa de mercado pelo prazo restante.
    """
    tc, tm   = taxa_compra / 100, taxa_mercado / 100
    restante = prazo_total_anos - tempo_decorrido_anos
    # VF do título na data de avaliação (acumulado pela taxa de compra)
    vf_titulo = valor * (1 + tc) ** prazo_total_anos
    # Preço MTM = VF descontado pela taxa de mercado pelo prazo restante
    preco_mtm = vf_titulo / (1 + tm) ** restante
    # Custo carregado até hoje
    preco_hoje = valor * (1 + tc) ** tempo_decorrido_anos
    variacao   = (preco_mtm / preco_hoje - 1) * 100
    duration   = restante / 2
    sensib     = -duration * (tm - tc) / (1 + tc) * 100
    return {
        "preco_teorico": round(preco_mtm, 2),
        "variacao_pct":  round(variacao, 4),
        "duration_anos": round(duration, 2),
        "sensibilidade": round(sensib, 4),
        "agio":          variacao >= 0,
    }
