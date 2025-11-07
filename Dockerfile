# Usa uma imagem oficial e leve do Python
FROM python:3.9-slim

# Define o "caminho" (path) do Python para que ele encontre o 'src'
ENV PYTHONPATH="/app"

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# --- PASSO DE CORREÇÃO v2 ---
# Adicionamos 'libglib2.0-0' para corrigir o novo erro 'libgthread-2.0.so.0'
# (provavelmente outra dependência do OpenCV ou GStreamer)
RUN apt-get update && \
    apt-get install -y \
        libgl1 \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*
# ----------------------------------------------------------------------

# Copia a lista de compras primeiro (para o cache do Docker)
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia TODO o seu projeto (src, runs, etc.) para dentro do contêiner
COPY . .

# Expõe a porta que o Uvicorn vai usar
EXPOSE 8000

# O comando para iniciar o servidor
CMD ["python", "-m", "uvicorn", "src.yoloDetectionV3.main:app", "--host", "0.0.0.0", "--port", "8000"]