# Em: src/yolodetectionv3/routers/auth_router.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

# ✅ CORREÇÃO: Importações absolutas começando com 'src.'
from src.yoloDetectionV3.controllers.auth_controller import auth_controller
from src.yoloDetectionV3.database import get_db_session, get_user_repo
from src.yoloDetectionV3.models.pydantic_models import UserCreate, Token, UserResponse
from src.yoloDetectionV3.models.database_models import Utilizador
from src.yoloDetectionV3.repositories.user_repository import UserRepository

router = APIRouter(
    # ✅ CORREÇÃO: O prefixo foi movido do main.py para cá
    # prefix="/auth", 
    tags=["Autenticação"]
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user: UserCreate, 
    repo: UserRepository = Depends(get_user_repo)
):
    return await auth_controller.register_user(user, repo)

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    repo: UserRepository = Depends(get_user_repo)
):
    return await auth_controller.login_for_access_token(form_data, repo)

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Utilizador = Depends(auth_controller.get_current_user_profile)
):
    return current_user