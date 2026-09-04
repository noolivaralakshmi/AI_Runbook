"""Dashboard API routes."""
from fastapi import APIRouter
from backend.database.connection import get_db
from backend.services.memory_service import get_all_memories

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard():
    """Get dashboard summary data."""
    db = get_db()

    total = db.execute("SELECT COUNT(*) as c FROM incidents").fetchone()["c"]
    resolved = db.execute("SELECT COUNT(*) as c FROM incidents WHERE status = 'resolved'").fetchone()["c"]
    active = db.execute("SELECT COUNT(*) as c FROM incidents WHERE status NOT IN ('resolved', 'failed')").fetchone()["c"]
    failed = db.execute("SELECT COUNT(*) as c FROM incidents WHERE status = 'failed'").fetchone()["c"]

    recent = db.execute(
        "SELECT id, title, status, severity, source, reporter, created_at FROM incidents ORDER BY created_at DESC LIMIT 10"
    ).fetchall()

    db.close()

    return {
        "stats": {
            "total": total,
            "resolved": resolved,
            "active": active,
            "failed": failed,
        },
        "recent_incidents": [dict(r) for r in recent],
    }


@router.get("/memory")
def get_memory():
    """Get stored incident memories."""
    return {"memories": get_all_memories()}
