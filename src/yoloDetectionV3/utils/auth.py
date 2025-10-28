from datetime import datetime, timedelta
from typing import Optional, Tuple, Any
from fastapi import Depends, HTTPException, status, WebSocket, Query, Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# =================================================================
# ✅ CORREÇÃO FINAL DA IMPORTAÇÃO (Usando o caminho RELATIVO simples)
# Isso deve ser o suficiente, pois os dois arquivos estão no mesmo nível.
# Se o erro persistir após esta correção, a falha está no sys.path do main.py
# ou em auth_router/auth_controller.
# =================================================================
from .database import get_db_session 

SECRET_KEY = "SUA_CHAVE_SECRETA_MUITO_FORTE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

# ... (funções verify_password, get_password_hash, create_access_token)
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

# =================================================================
# ✅ CORREÇÃO: Importa modelos dentro da função (Relativa)
# =================================================================
async def get_user(db: AsyncSession, username: str):
    # Importação do modelo: Usando a importação relativa do pacote 'models'
    from .models.database_models import Utilizador 
    query = select(Utilizador).where(Utilizador.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()

# ... (funções authenticate_user, get_utilizador_atual)

async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_utilizador_atual(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db_session)):
    from .models.database_models import Utilizador 
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
    
    user = await get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# =================================================================
# ✅ Adaptação para WebSockets
# =================================================================
async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db_session),
    token: Optional[str] = Query(None, alias="token"),
    session_cookie: Optional[str] = Cookie(None, alias="access_token")
):
    from .models.database_models import Utilizador 
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente.")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user(db, username=username)
    if user is None:
        raise credentials_exception
        
    return user 
