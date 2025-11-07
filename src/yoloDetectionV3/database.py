# Em: src/yolodetectionv3/database.py

import os
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# Importa BaseSettings do local correto (Pydantic v2+)
from pydantic_settings import BaseSettings

# Esta classe inteligente vai ler as variáveis do seu arquivo .env
class Settings(BaseSettings):
    db_user: str = "postgres"
    db_password: str = "password"
    db_host: str = "localhost"
    db_port: int = 5200
    db_name: str = "tcc_soja"

    class Config:
        # Encontra o arquivo .env na pasta raiz do projeto
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')

settings = Settings()

# Monta a URL de conexão para o SQLAlchemy
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@"
    f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

# Configura o "motor" do SQLAlchemy que gerencia a conexão
engine = create_async_engine(DATABASE_URL)
# Cria uma fábrica de sessões para interagir com o banco
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
# Uma classe base para nossos modelos de tabela
Base = declarative_base()

# ======================================================================
# INJEÇÃO DE DEPENDÊNCIAS (SESSÃO E REPOSITÓRIOS)
# ======================================================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Retorna uma sessão de banco de dados assíncrona, garantindo que seja fechada."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# --- Importações dos Repositórios ---
# ✅ CORREÇÃO: Todas as importações absolutas agora começam com 'src.'
from src.yoloDetectionV3.repositories.analise_repository import AnaliseRepository
from src.yoloDetectionV3.repositories.user_repository import UserRepository


async def get_analise_repo(
    session: AsyncSession = Depends(get_db_session)
) -> AnaliseRepository:
    """
    Dependência do FastAPI para injetar o AnaliseRepository com uma sessão.
    """
    return AnaliseRepository(session)


async def get_user_repo(
    session: AsyncSession = Depends(get_db_session)
) -> UserRepository:
    """
    Dependência do FastAPI para injetar o UserRepository com uma sessão.
    """
    return UserRepository(session)