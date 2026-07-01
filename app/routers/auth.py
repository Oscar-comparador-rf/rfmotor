"""
Auth v2 — Login com JWT, bloqueio de usuário, log de acesso.
CORRIGIDO: senha truncada para 72 bytes (limite bcrypt)
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.config import settings
import uuid

router  = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer()

USUARIOS: dict = {}
LOGS: list = []

def hash_senha(senha: str) -> str:
    """Hash seguro — trunca em 72 bytes (limite bcrypt)."""
    return pwd_ctx.hash(senha[:72])

def init_admin():
    if "admin@motorf.com" not in USUARIOS:
        USUARIOS["admin@motorf.com"] = {
            "id": str(uuid.uuid4()),
            "nome": "Admin",
            "senha_hash": hash_senha("admin2026"),
            "perfil": "sofisticado",
            "ativo": True,
            "admin": True,
            "criado_em": datetime.utcnow().isoformat(),
        }

init_admin()

class LoginInput(BaseModel):
    email: str
    senha: str

class CadastroInput(BaseModel):
    email: EmailStr
    nome: str
    senha: str
    perfil: str = "moderado"

class BloqueioInput(BaseModel):
    email: str
    ativo: bool

def criar_token(email: str, nome: str, admin: bool = False) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": email, "nome": nome, "admin": admin, "exp": exp},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if not email or email not in USUARIOS:
            raise HTTPException(status_code=401, detail="Token inválido")
        u = USUARIOS[email]
        if not u["ativo"]:
            raise HTTPException(status_code=403, detail="Acesso bloqueado.")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")

def verificar_admin(payload = Depends(verificar_token)):
    if not payload.get("admin"):
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return payload

@router.post("/login")
async def login(data: LoginInput, request: Request):
    email = data.email.lower().strip()
    u = USUARIOS.get(email)
    if not u or not pwd_ctx.verify(data.senha[:72], u["senha_hash"]):
        LOGS.append({"email": email, "nome": "—", "ip": request.client.host, "timestamp": datetime.utcnow().isoformat(), "acao": "LOGIN_FALHOU"})
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not u["ativo"]:
        LOGS.append({"email": email, "nome": u["nome"], "ip": request.client.host, "timestamp": datetime.utcnow().isoformat(), "acao": "LOGIN_BLOQUEADO"})
        raise HTTPException(status_code=403, detail="Acesso bloqueado.")
    LOGS.append({"email": email, "nome": u["nome"], "ip": request.client.host, "timestamp": datetime.utcnow().isoformat(), "acao": "LOGIN_OK"})
    token = criar_token(email, u["nome"], u.get("admin", False))
    return {"access_token": token, "token_type": "bearer", "nome": u["nome"], "perfil": u["perfil"], "admin": u.get("admin", False)}

@router.get("/me")
async def me(payload = Depends(verificar_token)):
    email = payload["sub"]
    u = USUARIOS[email]
    return {"email": email, "nome": u["nome"], "perfil": u["perfil"], "admin": u.get("admin", False)}

@router.post("/admin/cadastrar")
async def cadastrar(data: CadastroInput, payload = Depends(verificar_admin)):
    email = data.email.lower().strip()
    if email in USUARIOS:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    USUARIOS[email] = {"id": str(uuid.uuid4()), "nome": data.nome, "senha_hash": hash_senha(data.senha), "perfil": data.perfil, "ativo": True, "admin": False, "criado_em": datetime.utcnow().isoformat()}
    return {"msg": f"Usuário {data.nome} cadastrado com sucesso", "email": email}

@router.post("/admin/bloquear")
async def bloquear(data: BloqueioInput, payload = Depends(verificar_admin)):
    email = data.email.lower().strip()
    if email not in USUARIOS:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    USUARIOS[email]["ativo"] = data.ativo
    return {"msg": f"Usuário {email} {'desbloqueado' if data.ativo else 'bloqueado'}"}

@router.get("/admin/usuarios")
async def listar_usuarios(payload = Depends(verificar_admin)):
    return {"usuarios": [{"email": e, "nome": u["nome"], "perfil": u["perfil"], "ativo": u["ativo"], "admin": u.get("admin", False), "criado_em": u["criado_em"]} for e, u in USUARIOS.items()], "total": len(USUARIOS)}

@router.get("/admin/acessos")
async def listar_acessos(payload = Depends(verificar_admin)):
    return {"acessos": sorted(LOGS, key=lambda x: x["timestamp"], reverse=True)[:100], "total": len(LOGS)}

@router.delete("/admin/usuarios/{email}")
async def deletar_usuario(email: str, payload = Depends(verificar_admin)):
    email = email.lower().strip()
    if email not in USUARIOS:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if USUARIOS[email].get("admin"):
        raise HTTPException(status_code=400, detail="Não é possível deletar o admin")
    del USUARIOS[email]
    return {"msg": f"Usuário {email} removido"}
