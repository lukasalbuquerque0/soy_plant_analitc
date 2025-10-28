from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

# Importação relativa para o controller (para evitar o erro ModuleNotFoundError)
from ..controllers.auth_controller import auth_controller
# Importação relativa para os modelos de dependência e Pydantic
from ..database import get_db_session
from ..models.pydantic_models import UserCreate, Token, UserResponse

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"]
)

# Rota para Registro de Novo Utilizador
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db_session)):
    return await auth_controller.register_user(user, db)

# Rota para Login (Criação de Token JWT)
# Usa o esquema OAuth2PasswordRequestForm para receber username e password
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)):
    # ✅ CORREÇÃO: Chama o método com o nome correto 'login_for_access_token'
    return await auth_controller.login_for_access_token(form_data, db)

# Rota para obter detalhes do utilizador atual (requer token JWT)
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(auth_controller.get_current_user_profile)):
    return current_user
