import logging
from ultralytics import YOLO
import cv2  # Certifique-se que o opencv-python está instalado
import os
import numpy as np
from typing import Union # ✅ Importado para compatibilidade com Python < 3.10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YoloService:
    def __init__(self):
        self.model_path = "runs/detect/train11/weights/best.pt"
        self.model = self._load_model()
        # Estado do tracker para persistência entre frames individuais (se usar track)
        # ❗ Atenção: Gerenciar múltiplos clientes simultâneos pode exigir um tracker por conexão
        # self.tracker_state = {} # Exemplo para múltiplos clientes

    def _load_model(self):
        """Carrega o modelo YOLO do caminho especificado."""
        try:
            logger.info(f"A carregar o modelo YOLO de: {self.model_path}")
            # Considerar usar modo 'cpu' explicitamente se não tiver GPU ou para consistência
            # model = YOLO(self.model_path, task='detect', device='cpu')
            model = YOLO(self.model_path)
            logger.info("Modelo YOLO carregado com sucesso.")
            return model
        except Exception as e:
            logger.error(f"FALHA AO CARREGAR O MODELO YOLO: {e}", exc_info=True) # Log completo do erro
            return None

    def is_model_loaded(self) -> bool:
        """Verifica se o modelo YOLO foi carregado com sucesso."""
        return self.model is not None

    def get_model_info(self) -> Union[dict, None]: # ✅ CORRIGIDO type hint para Python < 3.10
        """Retorna informações sobre o modelo carregado ou None."""
        if self.is_model_loaded():
            # Tentar obter mais detalhes do modelo se possível
            try:
                # Nota: A API exata para obter detalhes pode variar entre versões do ultralytics
                model_type = "YOLOv8" # Assumindo v8
                # info = self.model.info() # Exemplo, verificar documentação
                # task = info.get('task', 'detect')
                return {"path": self.model_path, "type": model_type}
            except Exception:
                 logger.warning("Não foi possível obter detalhes específicos do modelo YOLO.", exc_info=True)
                 return {"path": self.model_path, "type": "YOLO (detalhes indisponíveis)"}
        return None

    # ✅ FUNÇÃO ADICIONADA para processar frames individuais (WebSocket)
    def process_single_frame(self, frame: np.ndarray) -> tuple[np.ndarray, Union[list[int], None]]:
        """
        Processa um único frame (imagem NumPy BGR) com o modelo YOLO,
        realiza o rastreamento (tracking), desenha as anotações e
        retorna o frame anotado e os IDs detectados/rastreados.

        Args:
            frame: A imagem (frame do vídeo) como um array NumPy BGR.

        Returns:
            Uma tupla contendo:
            - O frame anotado (como array NumPy BGR).
            - Uma lista de IDs inteiros detectados/rastreados neste frame, ou None.
        """
        if not self.is_model_loaded():
            logger.warning("Tentativa de processar frame único sem modelo carregado.")
            return frame, None # Retorna o frame original sem processamento

        try:
            # Usa track para manter IDs consistentes na sessão WebSocket
            results = self.model.track(
                source=frame,
                persist=True,      # Mantém estado do tracker (ATENÇÃO: pode não ser thread-safe)
                verbose=False,
                tracker="bytetrack.yaml",
                conf=0.33
            )

            if results and len(results) > 0:
                result = results[0]
                annotated_frame = result.plot() # Desenha caixas, labels, IDs

                current_ids = None
                if result.boxes is not None and result.boxes.id is not None:
                    current_ids = result.boxes.id.int().cpu().tolist()

                return annotated_frame, current_ids
            else:
                # logger.debug("Nenhuma detecção no frame atual.") # Log opcional
                return frame, None # Retorna frame original se nada foi detectado

        except Exception as e:
            logger.error(f"Erro ao processar frame único com YOLO: {e}", exc_info=True)
            return frame, None # Retorna frame original em caso de erro

    # --- Função track_video (original, com melhorias) ---
    def track_video(self, input_path: str, output_path: str) -> int:
        """
        Processa um arquivo de vídeo, rastreia objetos, salva vídeo anotado
        e retorna a contagem final de IDs únicos.
        """
        if not self.is_model_loaded():
            logger.error("Tentativa de processar vídeo sem modelo carregado.")
            return 0

        # Garante que o diretório de saída exista
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        except OSError as e:
            logger.error(f"Erro ao criar diretório de saída '{os.path.dirname(output_path)}': {e}")
            return 0

        cap = None
        out = None
        try:
            # 1. Abrir vídeo de entrada
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
                fps = 25.0 # Usar float para VideoWriter

            # 3. Criar VideoWriter para saída
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Codec para .mp4
            out = cv2.VideoWriter(output_path, fourcc, float(fps), (frame_width, frame_height))
            if not out.isOpened():
                logger.error(f"Erro ao criar o ficheiro de vídeo de saída: {output_path}")
                return 0 # Não precisa liberar cap aqui, o finally fará isso

            logger.info(f"Iniciando processamento e anotação do vídeo: {input_path} -> {output_path}")

            # 4. Preparar gerador de tracking
            results_generator = self.model.track(
                source=input_path, stream=True, persist=True,
                conf=0.33, tracker="bytetrack.yaml", verbose=False
            )

            tracked_ids = set() # Conjunto para IDs únicos
            frame_count = 0

            # 5. Iterar sobre os frames
            for results in results_generator:
                frame_count += 1
                annotated_frame = results.plot() # Frame com anotações

                # Atualizar IDs únicos
                current_frame_ids = []
                if results.boxes is not None and results.boxes.id is not None:
                    ids = results.boxes.id.int().cpu().tolist()
                    current_frame_ids.extend(ids)
                    tracked_ids.update(ids) # Mais eficiente que loop for

                # 6. Desenhar contagem única no frame
                contagem_total_unicos = len(tracked_ids)
                text = f"Contagem Unica: {contagem_total_unicos}"
                position = (50, 80)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.5
                color = (0, 255, 0) # Verde BGR
                thickness = 3
                cv2.putText(annotated_frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)

                # 7. Escrever frame no vídeo de saída
                out.write(annotated_frame)

            logger.info(f"Processados {frame_count} frames para '{input_path}'.")

        except Exception as process_err:
            logger.error(f"Erro durante o processamento do vídeo {input_path}: {process_err}", exc_info=True)
            # Retorna 0 em caso de erro durante o processamento
            return 0

        finally:
            # 8. Libertar recursos SEMPRE que terminar (sucesso ou erro)
            if cap:
                cap.release()
            if out:
                out.release()
            logger.debug("Recursos de vídeo libertados.") # Mude para INFO se quiser ver sempre

        contagem_final = len(tracked_ids)
        logger.info(f"Análise concluída para '{input_path}'. Vídeo anotado salvo. Contagem final: {contagem_final}")

        return contagem_final

# Instancia o serviço (singleton)
# Tratamento de erro na inicialização para evitar que a app quebre se o modelo falhar ao carregar
try:
    yolo_service = YoloService()
    if not yolo_service.is_model_loaded():
         logger.warning("Instância YoloService criada, mas o modelo NÃO foi carregado.")
         # A aplicação pode continuar, mas as funções de análise falharão.
except Exception as init_err:
     logger.critical(f"Falha CRÍTICA ao instanciar YoloService: {init_err}", exc_info=True)
     # Define como None para que verificações posteriores (is_model_loaded) falhem seguramente
     yolo_service = None