# Em: src/yolodetectionv3/repositories/analise_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.database_models import Analise
from datetime import datetime
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class AnaliseRepository:
    """
    Esta classe centraliza toda a lógica de acesso ao banco de dados
    para a entidade 'Analise'.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_analise(
        self,
        utilizador_id: int,
        nome_arquivo_original: str,
        video_salvo_em: str,
        contagem_total_unicos: int,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        local_texto: Optional[str] = None
    ) -> Analise:
        """
        Cria e salva um novo registro de análise no banco de dados.
        (Esta é a lógica que estava no seu VideoController e WebSocketController)
        """
        try:
            nova_analise = Analise(
                utilizador_id=utilizador_id,
                nome_arquivo_original=nome_arquivo_original,
                video_salvo_em=video_salvo_em,
                data_analise=datetime.utcnow(),
                contagem_total_unicos=contagem_total_unicos,
                latitude=latitude,
                longitude=longitude,
                local_texto=local_texto
            )
            self.db.add(nova_analise)
            await self.db.commit()
            await self.db.refresh(nova_analise)
            logger.info(f"Análise (ID: {nova_analise.id}) criada com sucesso via repositório.")
            return nova_analise
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao criar análise no repositório: {e}", exc_info=True)
            raise e # Propaga o erro para o serviço que o chamou

    async def get_historico_por_utilizador(self, utilizador_id: int) -> List[Analise]:
        """
        Busca o histórico de análises de um usuário.
        (Esta é a lógica do seu VideoController.get_user_history)
        """
        query = select(Analise).where(Analise.utilizador_id == utilizador_id).order_by(Analise.data_analise.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def atualizar_contagem_analise(self, analise_id: int, contagem_final: int) -> Optional[Analise]:
        """
        Atualiza a contagem de uma análise existente (útil para o WebSocket antigo).
        """
        try:
            analise = await self.db.get(Analise, analise_id)
            if analise:
                analise.contagem_total_unicos = contagem_final
                await self.db.commit()
                await self.db.refresh(analise)
                logger.info(f"Análise (ID: {analise.id}) atualizada com contagem final {contagem_final}.")
                return analise
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Erro ao atualizar análise {analise_id}: {e}", exc_info=True)
            raise e