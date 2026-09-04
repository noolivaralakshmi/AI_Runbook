"""Incident data models."""
from pydantic import BaseModel
from typing import Optional, List


class CreateIncidentRequest(BaseModel):
    title: str
    description: str
    source: str = "slack"
    source_channel: Optional[str] = None
    source_user: Optional[str] = None


class ManualIncidentRequest(BaseModel):
    title: str
    description: str
    severity: Optional[str] = "UNKNOWN"
