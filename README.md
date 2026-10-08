Aplicação de Machine Learning na Contagem Automatizada de Pés de Soja

Projeto acadêmico desenvolvido para automatizar a detecção e contagem de plantas de soja utilizando técnicas de Machine Learning e visão computacional.

A aplicação utiliza uma API em Python/FastAPI, integrada a um modelo YOLO treinado para identificar plantas de soja em imagens e vídeos.

🚀 Tecnologias
Python
FastAPI
YOLO / Ultralytics
OpenCV
PostgreSQL
Docker
WebRTC
Git / GitHub
⚙️ Funcionalidades
Detecção e contagem automatizada de plantas;
Análise de vídeos;
Autenticação de usuários;
Armazenamento das análises;
Consulta ao histórico;
API documentada via Swagger.
▶️ Execução

Clone o projeto:

git clone https://github.com/lukasalbuquerque0/soy_plant_analitc.git
cd soy_plant_analitc

Crie o ambiente virtual e instale as dependências:

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

Inicie o banco de dados:

docker compose up -d db

Execute a API:

python -m uvicorn src.yoloDetectionV3.main:app --reload --host 0.0.0.0 --port 8000
📖 Documentação

Após iniciar a aplicação, acesse:

Swagger: http://localhost:8000/docs

Interface: http://localhost:8000/interface
