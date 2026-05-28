from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def listar():
    return {"carteiras": [], "msg": "Carteiras persistentes — implementação v2"}
