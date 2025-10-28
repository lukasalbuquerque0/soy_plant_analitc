import sys
from pathlib import Path
from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
# Importar AsyncSession corretamente
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
import asyncio
import platform
import traceback # Para logar exceções

# =================================================================
# EVENT LOOP POLICY (PARA WINDOWS)
# =================================================================
if platform.system() == "Windows":
    try:
        # Tenta definir a política de loop de eventos para Windows, se aplicável
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        # Ignora se a política já está definida ou em versões onde não é necessário/possível
        pass

# Configura o path para importações corretas dentro do projeto
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir.parent)) # Adiciona a pasta 'src' ao path
sys.path.insert(0, str(current_dir))        # Adiciona a pasta 'yoloDetectionV3' ao path

# =================================================================
# IMPORTAÇÕES DO PROJETO (Após configurar o path)
# =================================================================
# Dependências do Banco de Dados
try:
    # Assume que database.py define engine, Base e get_db_session (async)
    from .database import engine, Base, get_db_session
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Falha ao importar de .database: {e}")
    print(f"Verifique se o ficheiro 'database.py' existe em '{current_dir}' e define 'engine', 'Base', 'get_db_session'.")
    sys.exit(1)

# Controllers
try:
    from .controllers.websocket_controller import WebSocketController
    from .controllers.video_controller import video_controller
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Falha ao importar controllers: {e}")
    print("Verifique os caminhos e nomes dos ficheiros nas pastas 'controllers'.")
    sys.exit(1)

# Autenticação (Importa a função específica para WS)
try:
    from .services.auth import get_current_user_ws
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Falha ao importar 'get_current_user_ws' de .services.auth: {e}")
    print("Verifique se a função existe e o caminho está correto.")
    sys.exit(1)

# Modelos (Necessário para o type hint de current_user)
try:
    from .models.database_models import Utilizador # Importa a classe real
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Falha ao importar 'Utilizador' de .models.database_models: {e}")
    print("Verifique se o ficheiro e a classe existem.")
    sys.exit(1)

# Routers (Importação relativa)
try:
    from .routers import auth_router, video_router, public_router
except ImportError as e:
    print(f"❌ ERRO CRÍTICO: Falha ao importar routers de .routers: {e}")
    print("Verifique os ficheiros na pasta 'routers'.")
    sys.exit(1)

# Instanciação do Controller WebSocket (Após importações)
websocket_controller = WebSocketController()

# Inicialização da API
app = FastAPI(
    title="Plataforma de Análise de Soja",
    version="3.2.2 (Startup Corrigido)", # Incrementa versão
    description="API para processar vídeos de plantações de soja, gerir utilizadores e consultar históricos."
)

# =====================================================================
# Middleware de CORS
# =====================================================================
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    # Adicione outras origens permitidas aqui (ex: IP da sua máquina, frontend de produção)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =====================================================================

# Eventos de Startup
@app.on_event("startup")
async def on_startup():
    print("[INFO] Verificando e criando tabelas do banco de dados...")
    try:
        # Inicializa a conexão com o banco e cria tabelas se não existirem
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ [SUCESSO] Tabelas do banco de dados prontas.")
    except Exception as e:
        print(f"❌ [ERRO] Falha ao conectar ou criar tabelas: {e}")
        traceback.print_exc() # Imprime o stack trace completo do erro

    # Verifica o status do modelo YOLO
    print("\n🔍 VERIFICAÇÃO DO MODELO YOLO:")
    try:
        # ✅ CORRIGIDO: Adicionado 'await' para chamar a função assíncrona
        health_status = await video_controller.health_check()

        # Verifica o resultado retornado pela função health_check
        if isinstance(health_status, dict) and health_status.get('model_loaded'):
            print("🎉 Modelo YOLO carregado com sucesso!")
            model_info = health_status.get('model_info')
            if model_info and isinstance(model_info, dict):
                print(f"   📁 Local: {model_info.get('path', 'N/A')}")
            else:
                 print("   ⚠️ Informações detalhadas do modelo não disponíveis.")
        else:
            print("❌ ATENÇÃO: Modelo YOLO não foi carregado ou status inválido!")
            print("   Verifique o caminho no 'yolo_service.py' e se o ficheiro '.pt' existe.")

    except Exception as yolo_err:
         print(f"❌ ERRO ao verificar o modelo YOLO: {yolo_err}")
         traceback.print_exc()

    print("=" * 60)
    print("🚀 API de Análise de Soja está online e pronta para receber requisições.")
    print("=" * 60)

# Inclusão dos Routers da API REST
app.include_router(public_router.router)
app.include_router(auth_router.router)
app.include_router(video_router.router)

# =================================================================
# ENDPOINT WEBSOCKET DEFINIDO DIRETAMENTE AQUI
# =================================================================
@app.websocket("/ws/realtime") # Endpoint que o frontend chama
async def websocket_endpoint(
    websocket: WebSocket,
    # Obtém o usuário validado usando a dependência de autenticação WS
    current_user: Utilizador = Depends(get_current_user_ws),
    # Usa AsyncSession para a sessão do banco de dados
    db: AsyncSession = Depends(get_db_session)
):
    # Verifica se a autenticação foi bem-sucedida
    if not current_user:
        # A dependência get_current_user_ws já deve ter fechado a conexão
        print("[WARN] Tentativa de conexão WebSocket falhou na autenticação (usuário não encontrado).")
        return

    # Passa o WebSocket, o ID do usuário validado e a sessão Async do banco
    # para o controller que vai gerenciar a lógica da conexão.
    # Certifique-se que handle_websocket_connection espera AsyncSession
    await websocket_controller.handle_websocket_connection(websocket, current_user.id, db)

# Manuseamento de Erros Globais (Captura exceções não tratadas nas rotas HTTP)
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # Loga o erro completo no servidor para depuração
    print(f"❌ Erro global não capturado na rota HTTP {request.url.path}: {exc}")
    traceback.print_exc()

    # Retorna uma resposta JSON genérica para o cliente
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocorreu um erro interno inesperado no servidor."},
    )

# Ponto de Entrada (para desenvolvimento local)
if __name__ == "__main__":
    # Comando comum para rodar: python -m uvicorn src.yoloDetectionV3.main:app --host 0.0.0.0 --port 8000 --reload
    print("[INFO] Iniciando servidor Uvicorn para desenvolvimento...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)