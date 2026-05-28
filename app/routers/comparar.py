from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.services.motor import avaliar_ativo, marktomarket
from app.services.dados_mercado import buscar_dados_mercado

router = APIRouter()


class AtivoInput(BaseModel):
    tipo:        str
    indexador:   str
    taxa:        float
    prazo_dias:  int
    emissor:     str
    fgc:         bool = False
    fidc_rating: Optional[str] = None
    fidc_cart:   Optional[str] = None


class ComparacaoInput(BaseModel):
    ativos:  List[AtivoInput]
    perfil:  str = "moderado"


class MTMInput(BaseModel):
    taxa_compra:         float
    taxa_mercado:        float
    prazo_total_anos:    float
    tempo_decorrido_anos: float
    valor:               float = 1000.0


@router.post("/")
async def comparar_ativos(payload: ComparacaoInput):
    """
    Endpoint principal — recebe lista de ativos e perfil,
    retorna ranking completo com Sharpe, juro real, adequação, equivalências.
    """
    mkt = await buscar_dados_mercado()
    resultados = []

    for a in payload.ativos:
        r = avaliar_ativo(
            tipo=a.tipo, indexador=a.indexador, taxa=a.taxa,
            prazo_dias=a.prazo_dias, fgc=a.fgc,
            perfil=payload.perfil, mkt=mkt,
        )
        resultados.append({
            "emissor":           a.emissor,
            "tipo":              a.tipo,
            "indexador":         a.indexador,
            "taxa":              a.taxa,
            "prazo_dias":        a.prazo_dias,
            "fgc":               a.fgc,
            "fidc_rating":       a.fidc_rating,
            "bruto":             r.bruto,
            "ir":                r.ir,
            "liquido":           r.liquido,
            "juro_real":         r.juro_real,
            "vol":               r.vol,
            "sharpe":            r.sharpe,
            "benchmark_sharpe":  r.benchmark_sharpe,
            "adequacao":         r.adequacao,
            "motivo":            r.motivo,
            "equiv_cdi_pct":     r.equiv_cdi_pct,
            "equiv_ipca_sp":     r.equiv_ipca_sp,
            "melhor":            False,
            "melhor_tipo":       None,
        })

    # Ranking: adequados primeiro, depois por juro_real desc
    ordem = {"ok": 0, "warn": 1, "no": 2}
    resultados.sort(key=lambda x: (ordem[x["adequacao"]], -x["juro_real"]))

    # Marcar melhor (só "ok" recebe ★; se não houver, melhor "warn")
    melhor_ok   = next((r for r in resultados if r["adequacao"] == "ok"),   None)
    melhor_warn = next((r for r in resultados if r["adequacao"] == "warn"),  None)
    melhor = melhor_ok or melhor_warn
    if melhor:
        melhor["melhor"]      = True
        melhor["melhor_tipo"] = "ok" if melhor_ok else "warn"

    cdi_liq = mkt.cdi * (1 - 0.15)
    return {
        "mercado": {
            "selic":           mkt.selic,
            "cdi":             mkt.cdi,
            "ipca_12m":        mkt.ipca,
            "ipca_proj":       mkt.iproj,
            "juro_real":       round(mkt.selic - mkt.iproj, 2),
            "cdi_liq_nominal": round(cdi_liq, 2),
            "cdi_liq_real":    round(cdi_liq - mkt.iproj, 2),
        },
        "perfil":   payload.perfil,
        "ranking":  resultados,
        "total":    len(resultados),
    }


@router.post("/mtm")
def calc_mtm(payload: MTMInput):
    """Calcula mark-to-market estimado para saída antecipada."""
    return marktomarket(
        taxa_compra=payload.taxa_compra,
        taxa_mercado=payload.taxa_mercado,
        prazo_total_anos=payload.prazo_total_anos,
        tempo_decorrido_anos=payload.tempo_decorrido_anos,
        valor=payload.valor,
    )
