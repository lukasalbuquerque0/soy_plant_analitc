#src/yolodetectionv3/services/yolo_services
import logging
from ultralytics import YOLO
import cv2  # Certifique-se que o opencv-python está instalado
import os
import numpy as np
from typing import Union, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define o caminho absoluto para a raiz do projeto
# (Encontra o caminho deste arquivo e "sobe" 3 níveis: services -> yoloDetectionV3 -> src -> RAIZ)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

class YoloService:
    def __init__(self):
        # Constrói o caminho completo e absoluto para o modelo
        self.model_path = PROJECT_ROOT / "runs" / "detect" / "train11" / "weights" / "best.pt"
        
        self.model = self._load_model()
        
        # ✅ ==========================================================
        # ✅ CORREÇÃO: Cor alterada para Ciano (Azul Piscina)
        # ✅ (OpenCV usa BGR, então (Azul, Verde, Vermelho))
        # ✅ ==========================================================
        self.box_color = (255, 255, 0) # Ciano Brilhante (Azul + Verde)
        
        self.text_color = (0, 0, 0) # Preto (para o texto no fundo ciano)
        self.box_thickness = 2
        self.font_scale = 0.5
        self.font_thickness = 1

    def _load_model(self):
        """Carrega o modelo YOLO do caminho especificado."""
        try:
            logger.info(f"A carregar o modelo YOLO de: {self.model_path}")
            model = YOLO(self.model_path)
            logger.info("Modelo YOLO carregado com sucesso.")
            return model
        except Exception as e:
            logger.error(f"FALHA AO CARREGAR O MODELO YOLO: {e}", exc_info=True)
            return None

    def is_model_loaded(self) -> bool:
        """Verifica se o modelo YOLO foi carregado com sucesso."""
        return self.model is not None

    def get_model_info(self) -> Union[dict, None]:
        """Retorna informações sobre o modelo carregado ou None."""
        if self.is_model_loaded():
             try:
                 model_type = "YOLOv8" 
                 return {"path": str(self.model_path), "type": model_type} # Converte Path para str
             except Exception:
                 logger.warning("Não foi possível obter detalhes específicos do modelo YOLO.", exc_info=True)
                 return {"path": str(self.model_path), "type": "YOLO (detalhes indisponíveis)"}
        return None

    def process_single_frame(self, frame: np.ndarray) -> tuple[np.ndarray, Union[list[int], None]]:
        """
        Processa um único frame (para WebRTC) com o modelo YOLO,
        realiza o rastreamento (tracking) e retorna o frame anotado
        desenhando as caixas manualmente.
        """
        if not self.is_model_loaded():
            logger.warning("Tentativa de processar frame único sem modelo carregado.")
            return frame, None

        annotated_frame = frame.copy()
        current_ids = None

        try:
            results = self.model.track(
                source=frame,
                persist=True,
                verbose=False,
                tracker="bytetrack.yaml",
                conf=0.33
            )

            if results and len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                
                if boxes.id is not None:
                    current_ids = boxes.id.int().cpu().tolist()
                    
                    for i, box_coords in enumerate(boxes.xyxy):
                        x1, y1, x2, y2 = map(int, box_coords)
                        track_id = current_ids[i]
                        
                        # Desenha a caixa (bounding box)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), self.box_color, self.box_thickness)
                        
                        label = f"ID: {track_id}"
                        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.font_thickness)
                        
                        # Desenha o fundo do texto
                        cv2.rectangle(annotated_frame, (x1, y1 - h - 10), (x1 + w, y1 - 5), self.box_color, -1)
                        # Desenha o texto
                        cv2.putText(annotated_frame, label, (x1, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.text_color, self.font_thickness, cv2.LINE_AA)

                return annotated_frame, current_ids
            else:
                return frame, None

        except Exception as e:
            logger.error(f"Erro ao processar frame único com YOLO: {e}", exc_info=True)
            return frame, None

    # ✅ ===================================================================
    # ✅ CORREÇÃO: track_video (Upload de Arquivo)
    # ✅ (Voltamos a usar o 'results_generator' estável + desenho manual)
    # ✅ ===================================================================
    def track_video(self, input_path: str, output_path: str) -> int:
        """
        Processa um arquivo de vídeo, rastreia objetos, salva vídeo anotado
        e retorna a contagem final de IDs únicos.
        """
        if not self.is_model_loaded():
            logger.error("Tentativa de processar vídeo sem modelo carregado.")
            return 0

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        except OSError as e:
            logger.error(f"Erro ao criar diretório de saída '{os.path.dirname(output_path)}': {e}")
            return 0

        cap = None
        out = None
        tracked_ids = set()
        
        try:
            # 1. Abrir vídeo de entrada (APENAS para obter as propriedades)
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                logger.error(f"Erro ao abrir o ficheiro de vídeo de entrada: {input_path}")
                return 0

            # 2. Obter propriedades do vídeo
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                logger.warning(f"FPS inválido ({fps}) detectado para {input_path}. Usando fallback de 25 FPS.")
                fps = 25.0
            cap.release() # Fecha o 'cap' pois o YOLO vai abrir o seu próprio

            # 3. Criar VideoWriter para saída
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, float(fps), (frame_width, frame_height))
            if not out.isOpened():
                logger.error(f"Erro ao criar o ficheiro de vídeo de saída: {output_path}")
                return 0

            logger.info(f"Iniciando processamento e anotação do vídeo (Contagem Estável): {input_path} -> {output_path}")

            # 4. Preparar gerador de tracking (O MÉTODO ESTÁVEL)
            results_generator = self.model.track(
                source=input_path, 
                stream=True, 
                persist=True,
                conf=0.33, 
                tracker="bytetrack.yaml", 
                verbose=False
                # Nota: Não usamos 'vid_stride' aqui para a contagem mais precisa
            )

            frame_count = 0

            # 5. Iterar sobre os frames
            for results in results_generator:
                frame_count += 1
                
                # Pega o frame original (imagem numpy)
                annotated_frame = results.orig_img.copy()

                if results.boxes is not None and results.boxes.id is not None:
                    boxes = results.boxes
                    ids = boxes.id.int().cpu().tolist()
                    tracked_ids.update(ids) # Atualiza IDs únicos
                    
                    # 6. Desenhar caixas manualmente com a cor Ciano
                    for i, box_coords in enumerate(boxes.xyxy):
                        x1, y1, x2, y2 = map(int, box_coords)
                        track_id = ids[i]
                        
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), self.box_color, self.box_thickness)
                        
                        label = f"ID: {track_id}"
                        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.font_thickness)
                        
                        cv2.rectangle(annotated_frame, (x1, y1 - h - 10), (x1 + w, y1 - 5), self.box_color, -1)
                        cv2.putText(annotated_frame, label, (x1, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.text_color, self.font_thickness, cv2.LINE_AA)

                # 7. Desenhar contagem única no frame
                contagem_total_unicos = len(tracked_ids)
                text = f"Contagem Unica: {contagem_total_unicos}"
                position = (50, 80)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.5
                color = self.box_color # Ciano
                thickness = 3
                cv2.putText(annotated_frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)

                # 8. Escrever frame no vídeo de saída
                out.write(annotated_frame)

            logger.info(f"Processados {frame_count} frames para '{input_path}'.")

        except Exception as process_err:
            logger.error(f"Erro durante o processamento do vídeo {input_path}: {process_err}", exc_info=True)
            return 0
        finally:
            # 9. Libertar recursos
            if cap and cap.isOpened():
                cap.release()
            if out and out.isOpened():
                out.release()
            logger.debug("Recursos de vídeo libertados.")

        contagem_final = len(tracked_ids)
        logger.info(f"Análise concluída para '{input_path}'. Vídeo anotado salvo. Contagem final: {contagem_final}")

        return contagem_final

# Instancia o serviço (singleton)
try:
    yolo_service = YoloService()
    if not yolo_service.is_model_loaded():
         logger.warning("Instância YoloService criada, mas o modelo NÃO foi carregado.")
except Exception as init_err:
     logger.critical(f"Falha CRÍTICA ao instanciar YoloService: {init_err}", exc_info=True)
     yolo_service = None