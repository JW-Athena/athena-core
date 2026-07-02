import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

from routes import register_routes
from athena_brain_routes import router as athena_brain_router
from organization_awareness_routes import router as organization_awareness_router
from organizational_knowledge_graph_routes import router as organizational_knowledge_graph_router


app = FastAPI(
    title="ATHENA Backend",
    description="ATHENA Business Operating System",
    version="0.2.0",
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
        "version": "0.2.0",
        "control_center": "http://127.0.0.1:8000/control",
        "openai_key_loaded": bool(
            os.getenv("OPENAI_API_KEY")
        ),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "backend": "running",
        "openai_key_loaded": bool(
            os.getenv("OPENAI_API_KEY")
        ),
        "version": "0.2.0",
    }


register_routes(app)
app.include_router(athena_brain_router)
app.include_router(organization_awareness_router)
app.include_router(organizational_knowledge_graph_router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
