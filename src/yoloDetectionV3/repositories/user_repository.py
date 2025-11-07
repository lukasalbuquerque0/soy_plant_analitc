# Em: src/yolodetectionv3/repositories/user_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.database_models import Utilizador
from ..models.pydantic_models import UserCreate # Importa o Pydantic model
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class UserRepository:
    """
    Centraliza toda a lógica de acesso ao banco de dados
    para a entidade 'Utilizador'.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username(self, username: str) -> Optional[Utilizador]:
        """
        Busca um utilizador pelo seu username.
        (Esta é a lógica da sua antiga função get_user em auth.py)
        """
        query = select(Utilizador).where(Utilizador.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Utilizador]:
        """
        Busca um utilizador pelo seu email (útil para verificação de registro).
        """
        query = select(Utilizador).where(Utilizador.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_user(self, user: UserCreate, hashed_password: str) -> Utilizador:
        """
        Cria um novo utilizador no banco de dados.
        (Esta é a lógica do seu AuthController.register_user)
        """
        try:
            db_user = Utilizador(
                username=user.username,
                email=user.email,
                hashed_password=hashed_password
            )
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"Utilizador {db_user.username} criado com sucesso.")
            return db_user
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao criar utilizador no repositório: {e}", exc_info=True)
            raise e # Propaga o erro