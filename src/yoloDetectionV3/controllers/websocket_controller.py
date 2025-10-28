import logging
from fastapi import WebSocket, WebSocketDisconnect, status # Adicionado status
from starlette.websockets import WebSocketState # Para verificar o estado
import numpy as np
import cv2
from sqlalchemy.ext.asyncio import AsyncSession # ✅ Importar AsyncSession
from datetime import datetime
import uuid # Para ID de sessão único
import traceback # Para log de erros

# ✅ CORREÇÃO FINAL: Usamos a importação relativa correta para o módulo 'models'
# Certifique-se que esta importação funciona na sua estrutura
try:
    from ..models.database_models import Analise
except ImportError as e:
     print(f"❌ ERRO CRÍTICO no websocket_controller: Falha ao importar 'Analise' de ..models.database_models: {e}")
     # Dependendo da sua necessidade, pode querer lançar um erro aqui
     Analise = None # Define como None para evitar NameError, mas o salvamento falhará


# Importar o serviço YOLO
# Certifique-se que esta importação funciona
try:
    from ..services.yolo_service import yolo_service
except ImportError as e:
     print(f"❌ ERRO CRÍTICO no websocket_controller: Falha ao importar 'yolo_service' de ..services.yolo_service: {e}")
     yolo_service = None # Define como None

logger = logging.getLogger(__name__)

class WebSocketController:

    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        user_id: int,
        # ✅ CORRIGIDO: Espera AsyncSession diretamente
        db: AsyncSession
    ):
        await websocket.accept()
        logger.info(f"Cliente WebSocket conectado para User ID: {user_id}")
        session_id = str(uuid.uuid4()) # ID único para esta sessão WS
        analise_db = None # Variável para guardar o registo DB
        tracked_ids_session = set() # Guarda IDs únicos desta sessão

        # Verificar se o modelo YOLO está carregado ANTES do loop
        if not yolo_service or not yolo_service.is_model_loaded():
             logger.error(f"Modelo YOLO não carregado. Fechando WebSocket para User ID: {user_id}")
             await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Modelo IA não disponível")
             return

        try:
            # --- Criação do Registro de Análise Inicial ---
            try:
                # Obter lat/lon/local - idealmente, o cliente enviaria isso via WS
                # Por agora, usamos valores padrão ou nulos
                latitude_ws = None
                longitude_ws = None
                local_texto_ws = f"Live Feed WS - {session_id}"

                if Analise: # Só tenta criar se a importação funcionou
                    analise_db = Analise(
                        utilizador_id=user_id,
                        nome_arquivo_original="Live_Feed_WS",
                        video_salvo_em=f"ws_session_{session_id}", # Identificador
                        data_analise=datetime.utcnow(),
                        contagem_total_unicos=0,
                        latitude=latitude_ws,
                        longitude=longitude_ws,
                        local_texto=local_texto_ws
                    )
                    db.add(analise_db)
                    await db.commit()
                    await db.refresh(analise_db)
                    logger.info(f"Registro de Análise (ID: {analise_db.id}) criado para sessão WS {session_id}.")
                else:
                    logger.error("Classe 'Analise' não importada. Não foi possível criar registo no DB.")

            except Exception as db_init_err:
                 logger.error(f"Erro ao criar registro inicial de Análise para WS {session_id}: {db_init_err}", exc_info=True)
                 await db.rollback()
                 # Considerar fechar o WS se o registro inicial for crítico
                 # await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Erro ao iniciar sessão no DB")
                 # return

            # --- Loop Principal de Recebimento/Processamento ---
            while websocket.application_state == WebSocketState.CONNECTED:
                try:
                    # Recebe os bytes da imagem do cliente
                    bytes_data = await websocket.receive_bytes()

                    # Decodifica a imagem
                    nparr = np.frombuffer(bytes_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if frame is None:
                        logger.warning(f"Frame recebido inválido ou vazio para User ID: {user_id}")
                        continue # Pula para o próximo frame

                    # ❗ Chama a nova função 'process_single_frame' do yolo_service
                    #    Certifique-se que ela existe e é async se necessário
                    try:
                         # Assume que process_single_frame é síncrona por agora
                         # Se for async, use: await yolo_service.process_single_frame(frame)
                         annotated_frame, current_ids = yolo_service.process_single_frame(frame)
                    except AttributeError:
                         logger.error("Função 'process_single_frame' não encontrada no yolo_service. Usando fallback.")
                         # Fallback: Tentar usar o método antigo (pode ser pesado)
                         results = yolo_service.model(frame, verbose=False, persist=True, tracker="bytetrack.yaml") # Adicionado persist e tracker
                         annotated_frame = results[0].plot()
                         current_ids = None
                         if results[0].boxes.id is not None:
                              current_ids = results[0].boxes.id.int().cpu().tolist()
                    except Exception as yolo_err:
                         logger.error(f"Erro no processamento YOLO do frame: {yolo_err}")
                         annotated_frame = frame # Envia frame original em caso de erro
                         current_ids = None


                    # Atualiza o conjunto de IDs únicos da sessão
                    if current_ids:
                        tracked_ids_session.update(current_ids)

                    # Codifica o frame (original ou anotado) de volta para JPEG
                    is_success, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if not is_success:
                         logger.warning(f"Falha ao codificar frame JPEG para User ID: {user_id}")
                         continue

                    # Envia os bytes de volta para o cliente
                    await websocket.send_bytes(buffer.tobytes())

                # Trata a desconexão esperada do cliente
                except WebSocketDisconnect:
                    logger.info(f"WebSocketDisconnect recebido para User ID: {user_id}. Fechando loop.")
                    break # Sai do loop while

                # Captura outros erros dentro do loop (ex: falha no processamento)
                except Exception as loop_error:
                    logger.error(f"Erro DENTRO do loop WebSocket para User ID {user_id}: {loop_error}", exc_info=True)
                    # Considerar enviar uma mensagem de erro para o cliente antes de fechar
                    # await websocket.send_text(f"Erro no servidor: {loop_error}")
                    break # Sai do loop em caso de erro grave

        # Captura erros que podem ocorrer fora do loop (ex: erro na aceitação inicial)
        except Exception as outer_error:
            logger.error(f"Erro FORA do loop WebSocket para User ID {user_id}: {outer_error}", exc_info=True)
            # Tenta fechar a conexão se ainda estiver aberta
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Erro interno no servidor")

        # Bloco Finally: Executa SEMPRE ao sair do try (seja por desconexão normal ou erro)
        finally:
            logger.info(f"Cliente WebSocket desconectado (User ID: {user_id}). Iniciando salvamento final da análise.")

            # --- Lógica Final de Salvamento no Banco ---
            if analise_db and Analise: # Só salva se o registro inicial foi criado E a classe foi importada
                try:
                    contagem_final = len(tracked_ids_session)

                    # Atualiza o registro existente com a contagem final
                    analise_db.contagem_total_unicos = contagem_final
                    # Poderia atualizar um timestamp de fim ou status aqui também

                    await db.commit() # Usa await com a AsyncSession 'db'
                    logger.info(f"✅ Análise (ID: {analise_db.id}) finalizada e salva com {contagem_final} itens únicos.")

                except Exception as db_final_err:
                    logger.error(f"❌ ERRO ao salvar/atualizar a análise final (ID: {analise_db.id}) no banco: {db_final_err}", exc_info=True)
                    await db.rollback() # Desfaz quaisquer mudanças pendentes

            elif not Analise:
                 logger.error("Não foi possível salvar a análise final porque a classe 'Analise' não foi importada.")
            else:
                 logger.warning("Nenhum registo de análise inicial encontrado para salvar a contagem final.")

            # Limpeza adicional pode ser feita aqui se necessário

# Instancia o controller (se não for feito em outro lugar)
# websocket_controller = WebSocketController() # A instanciação já está no main.py