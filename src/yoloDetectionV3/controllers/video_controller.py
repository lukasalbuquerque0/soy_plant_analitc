# Ficheiro: src/yoloDetectionV3/controllers/video_controller.py
import os
import uuid
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status, Depends
from typing import List

# ✅ CORREÇÃO: Importações absolutas começando com 'src.'
from src.yoloDetectionV3.database import get_analise_repo
from src.yoloDetectionV3.repositories.analise_repository import AnaliseRepository
from src.yoloDetectionV3.services.video_processing import process_video_file
from src.yoloDetectionV3.services.yolo_service import yolo_service
from src.yoloDetectionV3.services.auth import get_utilizador_atual
from src.yoloDetectionV3.utils.helpers import get_current_timestamp_iso
from src.yoloDetectionV3.models.pydantic_models import AnaliseResponse, HistoricoAnaliseResponse
from src.yoloDetectionV3.models.database_models import Utilizador # Para type hint

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoController:
    
    async def analyze_video(
        self,
        file: UploadFile,
        latitude: float,
        longitude: float,
        local_texto: str,
        analise_repo: AnaliseRepository = Depends(get_analise_repo),
        current_user: Utilizador = Depends(get_utilizador_atual)
    ) -> AnaliseResponse:
        
        if not file.content_type.startswith("video/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Tipo de ficheiro não suportado. Por favor, envie um vídeo.",
            )

        try:
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            save_path = os.path.join("processed_videos", unique_filename)
            os.makedirs("processed_videos", exist_ok=True)

            contagem = await process_video_file(file, save_path) 
            
            nova_analise = await analise_repo.create_analise(
                utilizador_id=current_user.id,
                nome_arquivo_original=file.filename,
                video_salvo_em=save_path,
                contagem_total_unicos=contagem,
                latitude=latitude,
                longitude=longitude,
                local_texto=local_texto
            )
            
            logger.info(f"Análise {nova_analise.id} concluída para o utilizador {current_user.username}.")

            return AnaliseResponse(
                id=nova_analise.id,
                message="Vídeo processado com sucesso!",
                contagem_total_unicos=nova_analise.contagem_total_unicos,
                nome_arquivo_original=nova_analise.nome_arquivo_original
            )

        except Exception as e:
            logger.error(f"Erro ao processar o vídeo: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Não foi possível processar o vídeo. Erro: {str(e)}"
            )

    async def get_user_history(
        self, 
        analise_repo: AnaliseRepository = Depends(get_analise_repo),
        current_user: Utilizador = Depends(get_utilizador_atual)
    ) -> List[HistoricoAnaliseResponse]:
        
        historico = await analise_repo.get_historico_por_utilizador(current_user.id)
        
        response_list = []
        for analise in historico:
            if analise.data_analise:
                analise.data_analise = analise.data_analise.replace(tzinfo=timezone.utc)
            # ✅ CORREÇÃO: O Pydantic v2 usa .model_validate()
            response_list.append(HistoricoAnaliseResponse.model_validate(analise)) 
        
        return response_list

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