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
from capability_marketplace_routes import router as capability_marketplace_router
from organization_awareness_routes import router as organization_awareness_router
from organizational_knowledge_graph_routes import router as organizational_knowledge_graph_router
from athena_runtime_routes import router as athena_runtime_router
from event_bus_routes import router as event_bus_router
from desktop_agent_routes import router as desktop_agent_router
from athena_reasoning_routes import router as athena_reasoning_router
from athena_workflow_routes import router as athena_workflow_router
from athena_memory_routes import router as athena_memory_router
from athena_planner_routes import router as athena_planner_router
from athena_decision_routes import router as athena_decision_router
from executive_file_intelligence_loop_routes import router as executive_file_intelligence_loop_router
from executive_document_intelligence_loop_routes import router as executive_document_intelligence_loop_router
from executive_objective_routes import router as executive_objective_router
from executive_execution_plan_routes import router as executive_execution_plan_router
from engine_011_routes import router as engine_011_router
from engine_013_routes import router as engine_013_router
from engine_014_routes import router as engine_014_router
from engine_015_routes import router as engine_015_router
from engine_017_routes import router as engine_017_router
from engine_018_routes import router as engine_018_router
from engine_019_routes import router as engine_019_router
from engine_020_routes import router as engine_020_router
from engine_021_routes import router as engine_021_router
from engine_022_routes import router as engine_022_router
from engine_023_routes import router as engine_023_router
from engine_024_routes import router as engine_024_router


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
app.include_router(capability_marketplace_router)
app.include_router(organization_awareness_router)
app.include_router(organizational_knowledge_graph_router)
app.include_router(athena_runtime_router)
app.include_router(event_bus_router)
app.include_router(desktop_agent_router)
app.include_router(athena_reasoning_router)
app.include_router(athena_workflow_router)
app.include_router(athena_memory_router)
app.include_router(athena_planner_router)
app.include_router(athena_decision_router)
app.include_router(executive_file_intelligence_loop_router)
app.include_router(executive_document_intelligence_loop_router)
app.include_router(executive_objective_router)
app.include_router(executive_execution_plan_router)
app.include_router(engine_011_router)
app.include_router(engine_013_router)
app.include_router(engine_014_router)
app.include_router(engine_015_router)
app.include_router(engine_017_router)
app.include_router(engine_018_router)
app.include_router(engine_019_router)
app.include_router(engine_020_router)
app.include_router(engine_021_router)
app.include_router(engine_022_router)
app.include_router(engine_023_router)
app.include_router(engine_024_router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
