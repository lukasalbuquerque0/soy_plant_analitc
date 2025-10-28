# Ficheiro: src/yoloDetectionV3/routers/video_router.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

# ✅ CORREÇÃO: Removemos a importação do modelo Utilizador
from ..services.auth import get_utilizador_atual # Pega a dependência de autenticação
from ..database import get_db_session # Pega a dependência da sessão do DB
# ❌ REMOVIDO: from ..models.database_models import Utilizador 
from ..models.pydantic_models import AnaliseResponse, HistoricoAnaliseResponse
from ..controllers.video_controller import video_controller

# 💡 Ação necessária para corrigir o NameError (caso o modelo seja necessário mais tarde)
# O modelo Utilizador é importado apenas onde é estritamente necessário ou 
# é resolvido usando typing.TYPE_CHECKING ou a string literal.

router = APIRouter(
    prefix="/api/v1",
    tags=["Análise de Vídeo e Histórico"],
    dependencies=[Depends(get_utilizador_atual)]
)

@router.post("/analisar-video", response_model=AnaliseResponse)
async def analisar_video(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    local_texto: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_session),
    # ✅ CORREÇÃO APLICADA: Usamos a string literal 'Utilizador' no type hint 
    # para evitar a dupla definição de tabela. O FastAPI/Pydantic resolve isso em tempo de execução.
    current_user: 'Utilizador' = Depends(get_utilizador_atual)
):
    return await video_controller.analyze_video(file, latitude, longitude, local_texto, db, current_user)

@router.get("/historico", response_model=List[HistoricoAnaliseResponse])
async def get_historico_do_utilizador(
    db: AsyncSession = Depends(get_db_session),
    # ✅ CORREÇÃO APLICADA: Usamos a string literal 'Utilizador'
    current_user: 'Utilizador' = Depends(get_utilizador_atual)
):
    return await video_controller.get_user_history(db, current_user)
