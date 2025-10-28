import logging
import os
import uuid
from fastapi import UploadFile, HTTPException, status

# ESTE IMPORT AGORA VAI FUNCIONAR CORRETAMENTE
from services.yolo_service import yolo_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define um diretório para uploads temporários
TEMP_UPLOAD_DIR = "temp_uploads"
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


async def process_video_file(file: UploadFile, save_path: str) -> int:
    """
    Salva o ficheiro de vídeo enviado num local temporário,
    processa-o com o YOLO (que salva um novo vídeo anotado em 'save_path'),
    e depois limpa o ficheiro temporário.
    """
    
    # Cria um caminho temporário único para o ficheiro de upload
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(TEMP_UPLOAD_DIR, temp_filename)

    try:
        # 1. Salvar o upload original no caminho temporário
        logger.info(f"A salvar o vídeo temporário em: {temp_path}")
        file_content = await file.read()
        with open(temp_path, "wb") as buffer:
            buffer.write(file_content)
        logger.info("Vídeo temporário salvo com sucesso.")

        if not yolo_service.is_model_loaded():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Modelo YOLO não está carregado. Não é possível processar o vídeo."
            )
        
        # 2. Chamar o serviço YOLO, que agora lê do temp_path e salva em save_path
        logger.info(f"Iniciando análise YOLO para o ficheiro: {temp_path}")
        logger.info(f"O vídeo anotado será salvo em: {save_path}")
        
        contagem = yolo_service.track_video(
            input_path=temp_path, 
            output_path=save_path
        )
        
        logger.info(f"Análise concluída. Contagem total: {contagem}")
        
        return contagem

    except Exception as e:
        logger.error(f"Falha crítica no processamento de vídeo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar o ficheiro de vídeo: {str(e)}"
        )
    
    finally:
        # 3. Limpar o ficheiro temporário, independentemente de sucesso ou falha
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Ficheiro temporário removido: {temp_path}")
            except Exception as e:
                logger.error(f"Não foi possível remover o ficheiro temporário {temp_path}: {e}")