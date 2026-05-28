from fastapi import APIRouter
from app.services.dados_mercado import buscar_dados_mercado, invalidar_cache

router = APIRouter()


@router.get("/")
async def get_mercado():
    """Retorna indicadores de mercado atualizados via BCB."""
    mkt = await buscar_dados_mercado()
    cdi_liq = mkt.cdi * (1 - 0.15)
    return {
        "selic":           mkt.selic,
        "cdi":             mkt.cdi,
        "ipca_12m":        mkt.ipca,
        "ipca_proj":       mkt.iproj,
        "juro_real":       round(mkt.selic - mkt.iproj, 2),
        "cdi_liq_nominal": round(cdi_liq, 2),
        "cdi_liq_real":    round(cdi_liq - mkt.iproj, 2),
    }


@router.post("/refresh")
async def refresh_mercado():
    """Força atualização do cache de mercado."""
    invalidar_cache()
    return await get_mercado()
