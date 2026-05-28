from fastapi import APIRouter
router = APIRouter()

@router.get("/tipos")
def listar_tipos():
    return {
        "bancarios": [
            {"id":"cdb",  "nome":"CDB",           "isento":False,"fgc":True},
            {"id":"lci",  "nome":"LCI",            "isento":True, "fgc":True},
            {"id":"lca",  "nome":"LCA",            "isento":True, "fgc":True},
            {"id":"lc",   "nome":"LC",             "isento":False,"fgc":True},
        ],
        "publicos": [
            {"id":"tselic","nome":"Tesouro Selic", "isento":False,"fgc":False},
            {"id":"tipca", "nome":"Tesouro IPCA+", "isento":False,"fgc":False},
            {"id":"tpre",  "nome":"Tesouro Pré",   "isento":False,"fgc":False},
        ],
        "privados": [
            {"id":"deb",  "nome":"Debênture",       "isento":False,"fgc":False},
            {"id":"debi", "nome":"Deb. Incentivada","isento":True, "fgc":False},
            {"id":"cri",  "nome":"CRI",             "isento":True, "fgc":False},
            {"id":"cra",  "nome":"CRA",             "isento":True, "fgc":False},
        ],
        "fidc": [
            {"id":"fidc_sr","nome":"FIDC Sênior",    "isento":False,"fgc":False},
            {"id":"fidc_mz","nome":"FIDC Mezanino",  "isento":False,"fgc":False},
            {"id":"fidc_jr","nome":"FIDC Subordinado","isento":False,"fgc":False},
        ],
    }
