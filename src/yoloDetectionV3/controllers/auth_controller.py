# Ficheiro: src/yoloDetectionV3/controllers/auth_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

# Importação relativa para o módulo auth que está no mesmo nível.
# ✅ Importa apenas as funções necessárias (resolve problemas de ciclo de importação)
from ..services.auth import (
    authenticate_user, 
    create_access_token, 
    get_utilizador_atual,
    get_password_hash,
    get_user # Adicionado para verificar unicidade no registro
)
# Modelos para criação de usuário e resposta (Pydantic pode ficar no topo)
from ..models.pydantic_models import UserCreate, Token, UserResponse 
from ..database import get_db_session # Dependência para obter a sessão do DB

# O auth_controller será instanciado na pasta controllers/__init__.py 
# ou no main.py, dependendo da arquitetura. Vamos manter a classe.

class AuthController:
    """
    Controlador para as rotas de Autenticação e Gestão de Utilizadores.
    """
    
    async def register_user(self, user: UserCreate, db: AsyncSession = Depends(get_db_session)):
        # 💡 Importa Utilizador DENTRO da função (Necessário para a lógica de DB)
        from ..models.database_models import Utilizador
        
        # 1. Verificar se o utilizador ou email já existe
        if await get_user(db, user.username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de utilizador já registado.")
        
        # 2. Hash da password
        hashed_password = get_password_hash(user.password)
        
        # 3. Criar novo utilizador
        db_user = Utilizador(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        
        # 4. Adicionar e persistir no banco de dados
        try:
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            return UserResponse.model_validate(db_user)
        except Exception as e:
            await db.rollback()
            # Este erro pode pegar violação de unicidade do email
            if "duplicate key value violates unique constraint" in str(e):
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registado.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro no registo: {e}")

    async def login_for_access_token(self, form_data: UserCreate, db: AsyncSession = Depends(get_db_session)):
        # 1. Autenticar o utilizador
        user = await authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nome de utilizador ou palavra-passe incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 2. Criar token JWT
        access_token = create_access_token(data={"sub": user.username})
        
        # 3. Retornar token e tipo
        return {"access_token": access_token, "token_type": "bearer"}

    async def get_current_user_profile(self, current_user: 'Utilizador' = Depends(get_utilizador_atual)):
        """Retorna os dados do utilizador logado (exclui a password hashed)."""
        # 💡 CORREÇÃO APLICADA: 'Utilizador' está entre aspas para evitar NameError no tempo de carregamento.
        return UserResponse.model_validate(current_user)

# Instanciamos o controller aqui para ser importado pelos routers
auth_controller = AuthController()
