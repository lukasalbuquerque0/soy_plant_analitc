# Em: src/yolodetectionv3/services/auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket, Query, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ CORREÇÃO: Importações absolutas começando com 'src.'
from src.yoloDetectionV3.database import get_user_repo, get_db_session
from src.yoloDetectionV3.repositories.user_repository import UserRepository
from src.yoloDetectionV3.models.database_models import Utilizador

SECRET_KEY = "SUA_CHAVE_SECRETA_MUITO_FORTE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") # Corrigido para /auth/login

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user(repo: UserRepository, username: str):
    return await repo.get_by_username(username)

async def authenticate_user(
    username: str, 
    password: str,
    repo: UserRepository
):
    user = await get_user(repo, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_utilizador_atual(
    token: str = Depends(oauth2_scheme), 
    repo: UserRepository = Depends(get_user_repo)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await repo.get_by_username(username=username) 
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_ws(
    websocket: WebSocket,
    repo: UserRepository = Depends(get_user_repo), 
    token: Optional[str] = Query(None, alias="token"),
    session_cookie: Optional[str] = Cookie(None, alias="access_token")
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticação ausente ou inválido no WebSocket handshake.",
    )
    
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif token:
        pass 
    elif session_cookie:
        token = session_cookie
    else:
        # ✅ CORREÇÃO: Lança a exceção corretamente
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await repo.get_by_username(username=username) 
    if user is None:
        raise credentials_exception
        
    return user