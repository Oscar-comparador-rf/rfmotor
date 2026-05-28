"""
Serviço de dados de mercado — BCB API + cache em memória (4h TTL).
Fallback para valores COPOM/IBGE mais recentes se API indisponível.
"""
import httpx
from datetime import datetime, timedelta
from app.services.motor import DadosMercado

_cache: dict = {}
_cache_ttl   = timedelta(hours=4)

SERIES_BCB = {
    "selic_meta": 432,    # Meta Selic % a.a. (COPOM)
    "ipca_12m":   13522,  # IPCA acumulado 12 meses
}

# Fallback — atualizar após cada reunião do COPOM
FALLBACK = DadosMercado(selic=14.50, cdi=14.40, ipca=4.39, iproj=4.50)


async def buscar_dados_mercado() -> DadosMercado:
    """
    Retorna indicadores de mercado.
    Usa cache de 4h. Se BCB indisponível, retorna fallback calibrado.
    """
    agora = datetime.utcnow()
    if "dados" in _cache and agora - _cache["ts"] < _cache_ttl:
        return _cache["dados"]

    mkt = DadosMercado(
        selic=FALLBACK.selic, cdi=FALLBACK.cdi,
        ipca=FALLBACK.ipca,   iproj=FALLBACK.iproj
    )

    async with httpx.AsyncClient(timeout=8.0) as client:
        # Selic meta (série 432 — já retorna % a.a., não daily)
        try:
            r = await client.get(
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs."
                f"{SERIES_BCB['selic_meta']}/dados/ultimos/1?formato=json"
            )
            if r.status_code == 200:
                d = r.json()
                if d:
                    mkt.selic = float(d[0]["valor"])
                    mkt.cdi   = round(mkt.selic - 0.10, 2)
        except Exception:
            pass

        # IPCA 12 meses
        try:
            r2 = await client.get(
                f"https://api.bcb.gov.br/dados/serie/bcdata.sgs."
                f"{SERIES_BCB['ipca_12m']}/dados/ultimos/1?formato=json"
            )
            if r2.status_code == 200:
                d2 = r2.json()
                if d2:
                    mkt.ipca = float(d2[0]["valor"])
        except Exception:
            pass

    _cache["dados"] = mkt
    _cache["ts"]    = agora
    return mkt


def invalidar_cache():
    """Força refresh na próxima chamada."""
    _cache.clear()
