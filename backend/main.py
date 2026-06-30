from fastapi import FastAPI

app = FastAPI(title="Athena Core API", version="0.1")

@app.get("/")
def root():
    return {
        "status": "Athena Core is alive",
        "version": "0.1",
        "mission": "Generate executive decision briefs from business documents"
    }
