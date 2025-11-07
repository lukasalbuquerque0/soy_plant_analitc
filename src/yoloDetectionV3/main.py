# Em: src/yolodetectionv3/main.py

import sys
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import platform
import traceback

# =================================================================
# ❌ BLOCO DE 'sys.path' REMOVIDO DAQUI
# (O 'FILE = Path...' e 'sys.path.append(str(ROOT))' foi apagado)
# O seu comando uvicorn já cuida disso.
# =================================================================

# =================================================================
# EVENT LOOP POLICY (PARA WINDOWS)
# =================================================================
if platform.system() == "Windows":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

# =================================================================
# IMPORTAÇÕES DO PROJETO
# =================================================================
try:
    # ✅ CORREÇÃO: Todas as importações absolutas agora começam com 'src.'
    from src.yoloDetectionV3.database import engine, Base
    from src.yoloDetectionV3.controllers.video_controller import video_controller
    from src.yoloDetectionV3.routers import auth_router, video_router, public_router
    from src.yoloDetectionV3.routers import webrtc_router 
except ImportError as e:
    # Este erro agora será muito mais preciso se algo falhar
    print(f"❌ ERRO CRÍTICO: Falha ao importar módulo. {e}")
    print("Verifique os nomes das pastas e se os arquivos '__init__.py' existem.")
    sys.exit(1)
# =================================================================

# =================================================================
# INICIALIZAÇÃO DA API
# =================================================================
app = FastAPI(
    title="Plataforma de Análise de Soja",
    version="4.0.4 (Importação 'src.' Corrigida)", # Nova versão
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
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ [SUCESSO] Tabelas do banco de dados prontas.")
    except Exception as e:
        print(f"❌ [ERRO] Falha ao conectar ou criar tabelas: {e}")
        traceback.print_exc()

    print("\n🔍 VERIFICAÇÃO DO MODELO YOLO:")
    try:
        # ✅ CORREÇÃO: A importação do 'video_controller' agora funciona
        health_status = await video_controller.health_check()
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

# =================================================================
# INCLUSÃO DOS ROUTERS
# =================================================================
app.include_router(public_router.router)
app.include_router(auth_router.router, prefix="/auth", tags=["Autenticação"])
app.include_router(video_router.router, prefix="/api/v1", tags=["Análise de Vídeo e Histórico"])

app.include_router(
    webrtc_router.router, 
    prefix="/api/v1/webrtc",
    tags=["WebRTC Real-time"]
)

# =================================================================
# Manuseamento de Erros Globais
# =================================================================
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    print(f"❌ Erro global não capturado na rota HTTP {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocorreu um erro interno inesperado no servidor."},
    )

# Ponto de Entrada
if __name__ == "__main__":
    print("[INFO] Iniciando servidor Uvicorn para desenvolvimento...")
    uvicorn.run(app, host="0.0.0.0", port=8000)