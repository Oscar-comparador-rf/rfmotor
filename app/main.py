from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, ativos, mercado, carteira, comparar

app = FastAPI(
    title="Motor Renda Fixa API",
    description="Comparador inteligente de ativos de renda fixa brasileira",
    version="1.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir em produção para domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",     tags=["auth"])
app.include_router(mercado.router,  prefix="/api/mercado",  tags=["mercado"])
app.include_router(ativos.router,   prefix="/api/ativos",   tags=["ativos"])
app.include_router(carteira.router, prefix="/api/carteira", tags=["carteira"])
app.include_router(comparar.router, prefix="/api/comparar", tags=["comparar"])


@app.get("/", tags=["status"])
def root():
    return {
        "status":  "ok",
        "versao":  "1.5.0",
        "produto": "Motor Renda Fixa",
        "docs":    "/docs",
    }
