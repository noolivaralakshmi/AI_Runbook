"""Runbook - AI-Powered Incident Response Platform."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.connection import init_db
from backend.routes.incidents import router as incidents_router
from backend.routes.dashboard import router as dashboard_router

app = FastAPI(title="Runbook", description="AI-Powered Incident Response Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents_router)
app.include_router(dashboard_router)

# Initialize DB on startup
init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "runbook"}
