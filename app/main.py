from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, comparar

app = FastAPI(
    title="Motor Renda Fixa API",
    description="Comparador inteligente de ativos de renda fixa brasileira",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",    tags=["auth"])
app.include_router(comparar.router, prefix="/api/comparar", tags=["comparar"])

@app.get("/api/mercado/", tags=["mercado"])
async def get_mercado():
    from app.services.dados_mercado import buscar_dados_mercado
    mkt = await buscar_dados_mercado()
    cdi_liq = mkt.cdi * (1 - 0.15)
    return {
        "selic": mkt.selic, "cdi": mkt.cdi,
        "ipca_12m": mkt.ipca, "ipca_proj": mkt.iproj,
        "juro_real": round(mkt.selic - mkt.iproj, 2),
        "cdi_liq_nominal": round(cdi_liq, 2),
        "cdi_liq_real": round(cdi_liq - mkt.iproj, 2),
    }

@app.get("/", tags=["status"])
def root():
    return {"status": "ok", "versao": "2.0.0", "produto": "Motor Renda Fixa"}
