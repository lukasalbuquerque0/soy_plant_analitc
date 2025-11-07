# Em: src/yolodetectionv3/routers/webrtc_router.py

import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.yoloDetectionV3.services.auth import get_current_user_ws
from src.yoloDetectionV3.models.database_models import Utilizador
from src.yoloDetectionV3.services.webrtc_service import WebRTCConnectionHandler
from src.yoloDetectionV3.services.yolo_service import yolo_service
from src.yoloDetectionV3.database import AsyncSessionLocal 

router = APIRouter()
logger = logging.getLogger(__name__)

# ✅ CORREÇÃO: Não precisamos mais do 'active_connections' global
# O 'handler' será criado e gerenciado dentro do escopo da conexão.

@router.websocket("/ws/webrtc")
async def websocket_endpoint(
    websocket: WebSocket,
    user: Utilizador = Depends(get_current_user_ws),
):
    await websocket.accept()
    logger.info(f"Cliente WebSocket {user.username} (ID: {user.id}) conectado para sinalização.")
    
    # O handler será criado apenas quando a oferta chegar
    handler: WebRTCConnectionHandler = None 
    
    try:
        # Loop de Sinalização
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "offer":
                logger.info(f"Recebida 'offer' de {user.username}")
                
                # ✅ CORREÇÃO: Extrai a localização da oferta
                location_data = data.get("location", {})
                
                # ✅ CORREÇÃO: O Handler é criado AQUI
                handler = WebRTCConnectionHandler(
                    yolo_service=yolo_service, 
                    session_factory=AsyncSessionLocal, 
                    user=user,
                    # Passa os novos dados de localização
                    latitude=location_data.get("latitude"),
                    longitude=location_data.get("longitude"),
                    local_texto=location_data.get("local_texto")
                )
                
                resposta = await handler.criar_oferta_de_sinalizacao(
                    sdp=data["sdp"], 
                    type=data["type"]
                )
                await websocket.send_json(resposta)

            # (Você pode adicionar 'elif data["type"] == "ice-candidate":' aqui se necessário)

    except WebSocketDisconnect:
        logger.info(f"Cliente WebSocket {user.username} desconectado.")
        # Se o handler foi criado, nós o fechamos para salvar no banco
        if handler:
            await handler.fechar_conexao() 
            
    except Exception as e:
        logger.error(f"Erro no WebSocket de {user.username}: {e}", exc_info=True)
        if handler:
            await handler.fechar_conexao()