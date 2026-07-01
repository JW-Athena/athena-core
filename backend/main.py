import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

from capability_004_routes import router as capability_004_router
from capability_005_routes import router as capability_005_router
from capability_006_routes import router as capability_006_router
from capability_007_routes import router as capability_007_router
from engine_008_routes import router as engine_008_router
from engine_009_routes import router as engine_009_router


app = FastAPI(
    title="ATHENA Backend",
    description="ATHENA Business Operating System",
    version="0.0.9",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "system": "ATHENA",
        "status": "online",
        "version": "0.0.9",
        "active_engine": "009 - RAG Answer Engine",
        "openai_key_loaded": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "backend": "running",
        "openai_key_loaded": bool(os.getenv("OPENAI_API_KEY")),
        "env_path": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
        "env_file_size": ENV_PATH.stat().st_size if ENV_PATH.exists() else 0,
        "capability_004": "ready",
        "capability_005": "ready",
        "capability_006": "ready",
        "capability_007": "ready",
        "engine_008": "ready",
        "engine_009": "ready",
    }


app.include_router(capability_004_router)
app.include_router(capability_005_router)
app.include_router(capability_006_router)
app.include_router(capability_007_router)
app.include_router(engine_008_router)
app.include_router(engine_009_router)