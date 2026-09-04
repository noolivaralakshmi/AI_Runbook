"""Incident memory service - stores resolved incidents for future reference using semantic search."""
import json
import uuid
import numpy as np
from backend.database.connection import get_db


def store_incident_memory(incident_id: str, description: str, diagnosis: dict, remediation: dict):
    """Store a resolved incident in memory for future lookups."""
    db = get_db()

    summary = diagnosis.get("summary", description[:200])
    root_cause = diagnosis.get("root_cause", "Unknown")
    resolution = remediation.get("suggested_fix", "Unknown")

    # Generate embedding
    try:
        embedding = generate_embedding(f"{summary} {root_cause} {resolution}")
        embedding_json = json.dumps(embedding)
    except Exception:
        embedding_json = None

    db.execute(
        """INSERT OR REPLACE INTO incident_memory (id, incident_id, summary, root_cause, resolution, embedding, created_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
        (str(uuid.uuid4())[:12], incident_id, summary, root_cause, resolution, embedding_json)
    )
    db.commit()
    db.close()


def search_similar_incidents(description: str, top_k: int = 3) -> list:
    """Search for similar past incidents using semantic similarity."""
    db = get_db()
    rows = db.execute("SELECT * FROM incident_memory WHERE embedding IS NOT NULL").fetchall()
    db.close()

    if not rows:
        return []

    try:
        query_embedding = generate_embedding(description)
    except Exception:
        # Fallback to keyword search if embeddings unavailable
        return keyword_search(description)

    results = []
    for row in rows:
        stored_embedding = json.loads(row["embedding"])
        similarity = cosine_similarity(query_embedding, stored_embedding)
        results.append({
            "incident_id": row["incident_id"],
            "summary": row["summary"],
            "root_cause": row["root_cause"],
            "resolution": row["resolution"],
            "similarity": similarity,
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def keyword_search(description: str) -> list:
    """Fallback keyword search when embeddings are unavailable."""
    db = get_db()
    rows = db.execute("SELECT * FROM incident_memory ORDER BY created_at DESC LIMIT 5").fetchall()
    db.close()

    words = [w.lower() for w in description.split() if len(w) > 4]
    results = []
    for row in rows:
        text = f"{row['summary']} {row['root_cause']} {row['resolution']}".lower()
        if any(word in text for word in words):
            results.append({
                "incident_id": row["incident_id"],
                "summary": row["summary"],
                "root_cause": row["root_cause"],
                "resolution": row["resolution"],
                "similarity": 0.5,
            })
    return results[:3]


def generate_embedding(text: str) -> list:
    """Generate embedding using Bedrock Titan."""
    import boto3
    from backend.config import AWS_REGION

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    body = json.dumps({"inputText": text[:10000], "dimensions": 512, "normalize": True})

    response = client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def cosine_similarity(a: list, b: list) -> float:
    a = np.array(a)
    b = np.array(b)
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def get_all_memories() -> list:
    """Get all stored incident memories."""
    db = get_db()
    rows = db.execute(
        "SELECT incident_id, summary, root_cause, resolution, created_at FROM incident_memory ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]
