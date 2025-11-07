# Ficheiro: src/yoloDetectionV3/routers/video_router.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

# ✅ CORREÇÃO: Importações absolutas começando com 'src.'
from src.yoloDetectionV3.services.auth import get_utilizador_atual
from src.yoloDetectionV3.database import get_db_session, get_analise_repo # Importa o novo repo
from src.yoloDetectionV3.models.database_models import Utilizador
from src.yoloDetectionV3.models.pydantic_models import AnaliseResponse, HistoricoAnaliseResponse
from src.yoloDetectionV3.controllers.video_controller import video_controller
from src.yoloDetectionV3.repositories.analise_repository import AnaliseRepository


router = APIRouter(
    # ❌ CORREÇÃO: O prefixo "/api/v1" foi REMOVIDO daqui.
    # O 'main.py' já define o prefixo.
    tags=["Análise de Vídeo e Histórico"],
    dependencies=[Depends(get_utilizador_atual)]
)

@router.post("/analisar-video", response_model=AnaliseResponse)
async def analisar_video(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    local_texto: Optional[str] = Form(None),
    # ✅ CORREÇÃO: Injetando o Repositório
    repo: AnaliseRepository = Depends(get_analise_repo), 
    current_user: Utilizador = Depends(get_utilizador_atual)
):
    return await video_controller.analyze_video(
        file, latitude, longitude, local_texto, repo, current_user
    )

@router.get("/historico", response_model=List[HistoricoAnaliseResponse])
async def get_historico_do_utilizador(
    # ✅ CORREÇÃO: Injetando o Repositório
    repo: AnaliseRepository = Depends(get_analise_repo),
    current_user: Utilizador = Depends(get_utilizador_atual)
):
    return await video_controller.get_user_history(repo, current_user)