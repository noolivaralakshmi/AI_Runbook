"""Incident API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.pipeline_service import create_incident, get_incident, list_incidents, run_pipeline

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class CreateIncidentRequest(BaseModel):
    description: str
    reporter: str = "unknown"
    source: str = "discord"
    source_message_id: str = None
    source_channel_id: str = None


@router.post("")
def create_and_run(req: CreateIncidentRequest):
    """Create an incident and run the full AI pipeline."""
    incident = create_incident(
        description=req.description,
        reporter=req.reporter,
        source=req.source,
        source_message_id=req.source_message_id,
        source_channel_id=req.source_channel_id,
    )

    # Run the pipeline
    result = run_pipeline(incident["id"])
    return result


@router.post("/create")
def create_only(req: CreateIncidentRequest):
    """Create an incident without running pipeline (for manual trigger)."""
    return create_incident(
        description=req.description,
        reporter=req.reporter,
        source=req.source,
    )


@router.post("/{incident_id}/run")
def run_incident_pipeline(incident_id: str):
    """Run pipeline on an existing incident."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return run_pipeline(incident_id)


@router.get("/{incident_id}")
def get_incident_by_id(incident_id: str):
    """Get incident details with pipeline steps."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("")
def get_all_incidents(limit: int = 20):
    """List all incidents."""
    return {"incidents": list_incidents(limit)}
