# Em: src/yolodetectionv3/services/webrtc_service.py
import asyncio
import logging
import uuid
from typing import Set, Optional # ✅ Adicionado Optional
from fractions import Fraction

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.mediastreams import MediaStreamError
from av import VideoFrame

from src.yoloDetectionV3.services.yolo_service import YoloService
from src.yoloDetectionV3.repositories.analise_repository import AnaliseRepository 
from src.yoloDetectionV3.models.database_models import Utilizador
from src.yoloDetectionV3.database import AsyncSessionLocal 


logger = logging.getLogger(__name__)

class YoloVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.queue: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=30)
        self.counter = 0

    async def recv(self) -> VideoFrame:
        frame = await self.queue.get()
        frame.pts, frame.time_base = self.counter, Fraction(1, 30)
        self.counter += 1
        return frame

    async def push_frame(self, frame: VideoFrame):
        if self.queue.full():
            await self.queue.get()
        await self.queue.put(frame)


class WebRTCConnectionHandler:
    
    # ✅ ==========================================================
    # ✅ CORREÇÃO: O __init__ agora aceita os argumentos de localização
    # ✅ ==========================================================
    def __init__(self, yolo_service: YoloService, session_factory: AsyncSessionLocal, user: Utilizador,
                 latitude: Optional[float] = None, 
                 longitude: Optional[float] = None, 
                 local_texto: Optional[str] = None):
        
        self.pc = RTCPeerConnection()
        self.video_track_saida = YoloVideoStreamTrack()
        
        # Injetando suas dependências
        self.yolo_service = yolo_service
        self.session_factory = session_factory
        self.user = user 
        
        # ✅ Armazena a localização
        self.latitude = latitude
        self.longitude = longitude
        self.local_texto = local_texto
        
        self.tracked_ids: Set[int] = set()
        self.frame_counter = 0

        self.pc.addTrack(self.video_track_saida)

        @self.pc.on("track")
        async def on_track(track):
            logger.info(f"Track {track.kind} recebido de {self.user.username}")
            if track.kind == "video":
                asyncio.create_task(self.processar_video(track, self.video_track_saida))

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Estado da conexão de {self.user.username}: {self.pc.connectionState}")
            if self.pc.connectionState == "closed" or self.pc.connectionState == "failed":
                await self.salvar_analise() 
                await self.fechar_conexao()

    async def processar_video(self, track_entrada: VideoStreamTrack, track_saida: YoloVideoStreamTrack):
        img_processada = None 
        while True:
            try:
                frame = await track_entrada.recv()
                img = frame.to_ndarray(format="bgr24")
                
                self.frame_counter += 1
                
                if self.frame_counter % 3 == 0: 
                    img_processada_nova, ids_detectados = await asyncio.to_thread(
                        self.yolo_service.process_single_frame, img
                    )
                    if ids_detectados:
                        self.tracked_ids.update(ids_detectados)
                    img_processada = img_processada_nova
                
                if img_processada is None:
                    img_processada = img

                novo_frame = VideoFrame.from_ndarray(img_processada, format="bgr24")
                await track_saida.push_frame(novo_frame)
                
            except MediaStreamError:
                logger.info(f"Stream de {self.user.username} encerrado.")
                return
            except Exception as e:
                logger.error(f"Erro no processamento de vídeo de {self.user.username}: {e}", exc_info=True)
                return

    async def criar_oferta_de_sinalizacao(self, sdp, type):
        offer = RTCSessionDescription(sdp=sdp, type=type)
        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        return {"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type}

    async def salvar_analise(self):
        contagem = len(self.tracked_ids)
        if contagem == 0:
            logger.info(f"Nenhuma detecção para {self.user.username}. Análise não será salva.")
            return

        logger.info(f"Salvando análise para {self.user.username} com Contagem: {contagem}, Local: {self.local_texto}")
        
        try:
            async with self.session_factory() as session:
                repo = AnaliseRepository(session)
                
                unique_stream_name = f"webrtc_stream_{uuid.uuid4()}"
                
                # ✅ CORREÇÃO: Passa os dados de localização para o banco
                await repo.create_analise(
                    utilizador_id=self.user.id,
                    nome_arquivo_original=self.local_texto or "Live Stream WebRTC",
                    video_salvo_em=unique_stream_name,
                    contagem_total_unicos=contagem,
                    latitude=self.latitude,
                    longitude=self.longitude,
                    local_texto=self.local_texto
                )
            logger.info(f"Análise salva com sucesso (ID: {unique_stream_name}).")
        except Exception as e:
            logger.error(f"Falha ao salvar análise para {self.user.username}: {e}", exc_info=True)

    async def fechar_conexao(self):
        if self.pc.connectionState != "closed":
            await self.pc.close()
            logger.info(f"Conexão WebRTC de {self.user.username} fechada.")