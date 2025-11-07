# Ficheiro: src/yoloDetectionV3/controllers/auth_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ CORREÇÃO: Importações absolutas começando com 'src.'
from src.yoloDetectionV3.services.auth import (
    authenticate_user, 
    create_access_token, 
    get_utilizador_atual,
    get_password_hash
)
from src.yoloDetectionV3.models.pydantic_models import UserCreate, Token, UserResponse
from src.yoloDetectionV3.database import get_db_session, get_user_repo
from src.yoloDetectionV3.repositories.user_repository import UserRepository
from src.yoloDetectionV3.models.database_models import Utilizador


class AuthController:
    
    async def register_user(
        self, 
        user: UserCreate, 
        repo: UserRepository = Depends(get_user_repo)
    ) -> UserResponse:
        
        if await repo.get_by_username(user.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de utilizador já registado.")
        
        if await repo.get_by_email(user.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registado.")
            
        hashed_password = get_password_hash(user.password)
        
        try:
            db_user = await repo.create_user(user, hashed_password)
            # ✅ CORREÇÃO: Pydantic v2 usa .model_validate()
            return UserResponse.model_validate(db_user)
        except Exception as e:
            if "duplicate key value" in str(e):
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registado.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro no registo: {e}")

    async def login_for_access_token(
        self, 
        form_data: OAuth2PasswordRequestForm = Depends(), 
        repo: UserRepository = Depends(get_user_repo)
    ) -> Token:
        
        user = await authenticate_user(
            username=form_data.username, 
            password=form_data.password, 
            repo=repo
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nome de utilizador ou palavra-passe incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(data={"sub": user.username})
        
        return Token(access_token=access_token, token_type="bearer")

    async def get_current_user_profile(
        self, 
        current_user: Utilizador = Depends(get_utilizador_atual)
    ) -> UserResponse:
        # ✅ CORREÇÃO: Pydantic v2 usa .model_validate()
        return UserResponse.model_validate(current_user)

auth_controller = AuthController()