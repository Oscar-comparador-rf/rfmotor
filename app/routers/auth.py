from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.config import settings

router  = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreate(BaseModel):
    email:  EmailStr
    nome:   str
    senha:  str
    perfil: str = "moderado"

class LoginInput(BaseModel):
    email: EmailStr
    senha: str


def criar_token(email: str, nome: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": email, "nome": nome, "exp": exp},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


@router.post("/register")
async def register(user: UserCreate):
    """
    Registro de usuário — v1 simplificado (sem banco).
    v2: persistir no PostgreSQL.
    """
    token = criar_token(user.email, user.nome)
    return {"access_token": token, "token_type": "bearer",
            "nome": user.nome, "perfil": user.perfil}


@router.post("/login")
async def login(data: LoginInput):
    """Login — v1 simplificado. v2: validar hash no banco."""
    token = criar_token(data.email, "Usuário")
    return {"access_token": token, "token_type": "bearer"}
