from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from capability_004_routes import router as capability_004_router


app = FastAPI(
    title="ATHENA Backend",
    description="ATHENA Business Operating System",
    version="0.0.4",
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
        "version": "0.0.4",
        "active_capability": "004 - Executive Information Extraction",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "backend": "running",
        "capability_004": "ready",
    }


app.include_router(capability_004_router)