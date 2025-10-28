import os
import uuid
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

# ✅ CORREÇÃO FINAL: Usamos a importação relativa para a pasta vizinha 'models'
# A falha anterior estava na importação RELATIVA aqui.
from ..models.database_models import Analise 
# 💡 NOTA: A classe Utilizador será importada dentro da função get_user_history para evitar ciclos.

from services.video_processing import process_video_file
from services.yolo_service import yolo_service
from src.yoloDetectionV3.utils.helpers import get_current_timestamp_iso

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoController:
    async def analyze_video(
        self,
        file: UploadFile,
        latitude: float,
        longitude: float,
        local_texto: str,
        db: AsyncSession,
        current_user: 'Utilizador' # Usando string literal para evitar NameError/Ciclo
    ):
        if not file.content_type.startswith("video/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Tipo de ficheiro não suportado. Por favor, envie um vídeo.",
            )

        try:
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            save_path = os.path.join("processed_videos", unique_filename)
            
            os.makedirs("processed_videos", exist_ok=True)

            # NOTE: Assumindo que process_video_file é async e funciona
            contagem = await process_video_file(file, save_path) 
            
            nova_analise = Analise(
                utilizador_id=current_user.id,
                nome_arquivo_original=file.filename,
                video_salvo_em=save_path,
                
                data_analise=datetime.utcnow(),
                
                contagem_total_unicos=contagem,
                latitude=latitude,
                longitude=longitude,
                local_texto=local_texto
            )
            db.add(nova_analise)
            await db.commit()
            await db.refresh(nova_analise)
            
            logger.info(f"Análise {nova_analise.id} concluída para o utilizador {current_user.username}.")

            return {
                "id": nova_analise.id,
                "message": "Vídeo processado com sucesso!",
                "contagem_total_unicos": contagem
            }

        except Exception as e:
            logger.error(f"Erro ao processar o vídeo: {e}")
            await db.rollback() # Garante que a transação é limpa
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Não foi possível processar o vídeo. Erro: {str(e)}"
            )

    async def get_user_history(self, db: AsyncSession, current_user: 'Utilizador'):
        # 💡 Importamos Utilizador AQUI DENTRO para evitar ciclos na inicialização do módulo
        from ..models.database_models import Utilizador 

        query = select(Analise).where(Analise.utilizador_id == current_user.id).order_by(Analise.data_analise.desc())
        result = await db.execute(query)
        historico = result.scalars().all()
        
        for analise in historico:
            if analise.data_analise:
                # Garante que o timestamp é marcado como UTC para o frontend
                analise.data_analise = analise.data_analise.replace(tzinfo=timezone.utc) 
        
        return historico

    async def health_check(self):
        model_loaded = yolo_service.is_model_loaded()
        model_info = yolo_service.get_model_info() if model_loaded else None
        
        return {
            "status": "operacional" if model_loaded else "degradado",
            "timestamp": get_current_timestamp_iso(),
            "model_loaded": model_loaded,
            "model_info": model_info
        }

video_controller = VideoController()
