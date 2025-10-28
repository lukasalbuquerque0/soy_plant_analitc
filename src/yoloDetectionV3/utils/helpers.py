# Ficheiro: src/yoloDetectionV3/utils/helpers.py

from datetime import datetime, timezone

def get_current_timestamp_iso() -> str:
    """
    Retorna o timestamp atual em formato string ISO 8601 com timezone UTC.
    
    É uma boa prática usar UTC (Tempo Universal Coordenado) em servidores
    para evitar problemas com fusos horários.
    
    Exemplo de retorno: '2025-10-17T16:36:23.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()

# Pode adicionar outras funções úteis aqui no futuro.