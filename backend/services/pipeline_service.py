"""Incident response pipeline - orchestrates the full intake → diagnosis → remediation → execution flow."""
import json
import uuid
from datetime import datetime
from backend.database.connection import get_db, dict_from_row
from backend.services.ai_service import invoke_bedrock, parse_json_response
from backend.services.memory_service import search_similar_incidents, store_incident_memory
from backend.services.github_service import create_issue, create_pull_request
from backend.services.aws_connector import execute_aws_action
from backend.prompts.diagnosis import build_diagnosis_prompt
from backend.prompts.remediation import build_remediation_prompt


PIPELINE_STEPS = [
    {"name": "intake", "number": 1, "label": "Intake"},
    {"name": "diagnosis", "number": 2, "label": "Diagnostician"},
    {"name": "remediation", "number": 3, "label": "Remediator"},
    {"name": "execution", "number": 4, "label": "Connector Writes"},
    {"name": "memory", "number": 5, "label": "Memory Store"},
]


def create_incident(description: str, reporter: str = None, source: str = "discord",
                    source_message_id: str = None, source_channel_id: str = None) -> dict:
    """Create a new incident and initialize pipeline steps."""
    db = get_db()
    incident_id = str(uuid.uuid4())[:12]
    now = datetime.utcnow().isoformat()

    # Create incident
    db.execute(
        """INSERT INTO incidents (id, source, source_message_id, source_channel_id, reporter, description, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'intake', ?)""",
        (incident_id, source, source_message_id, source_channel_id, reporter, description, now)
    )

    # Create pipeline steps
    for step in PIPELINE_STEPS:
        db.execute(
            """INSERT INTO pipeline_steps (id, incident_id, step_name, step_number, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (str(uuid.uuid4())[:12], incident_id, step["name"], step["number"])
        )

    db.commit()
    db.close()
    return get_incident(incident_id)


def get_incident(incident_id: str) -> dict:
    """Get an incident with its pipeline steps."""
    db = get_db()
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not row:
        db.close()
        return None

    incident = dict_from_row(row)

    # Get pipeline steps
    steps = db.execute(
        "SELECT * FROM pipeline_steps WHERE incident_id = ? ORDER BY step_number",
        (incident_id,)
    ).fetchall()
    incident["pipeline"] = [dict_from_row(s) for s in steps]

    # Get connector activity
    activity = db.execute(
        "SELECT * FROM connector_activity WHERE incident_id = ? ORDER BY created_at",
        (incident_id,)
    ).fetchall()
    incident["activity"] = [dict_from_row(a) for a in activity]

    db.close()
    return incident


def list_incidents(limit: int = 20) -> list:
    """List recent incidents."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    db.close()
    return [dict_from_row(r) for r in rows]


def run_pipeline(incident_id: str) -> dict:
    """Run the full incident response pipeline."""
    incident = get_incident(incident_id)
    if not incident:
        return {"error": "Incident not found"}

    db = get_db()

    # Step 1: Intake (already done on creation)
    update_step(db, incident_id, "intake", "done")
    update_incident_status(db, incident_id, "diagnosing")

    # Step 2: Diagnosis
    update_step(db, incident_id, "diagnosis", "running")
    try:
        # Search past incidents for context
        past_incidents = search_similar_incidents(incident["description"])
        past_context = format_past_incidents(past_incidents)

        # Run AI diagnosis
        prompt = build_diagnosis_prompt(incident["description"], past_context)
        ai_response = invoke_bedrock(prompt)
        diagnosis = parse_json_response(ai_response)

        db.execute("UPDATE incidents SET diagnosis = ?, title = ? WHERE id = ?",
                   (json.dumps(diagnosis), diagnosis.get("title", "Incident"), incident_id))
        db.commit()

        update_step(db, incident_id, "diagnosis", "done", output=diagnosis)
    except Exception as e:
        diagnosis = {"error": str(e), "summary": "Diagnosis failed"}
        update_step(db, incident_id, "diagnosis", "failed", output=diagnosis)
        update_incident_status(db, incident_id, "failed")
        db.close()
        return get_incident(incident_id)

    # Step 3: Remediation
    update_step(db, incident_id, "remediation", "running")
    update_incident_status(db, incident_id, "remediating")
    try:
        prompt = build_remediation_prompt(incident["description"], json.dumps(diagnosis), past_context)
        ai_response = invoke_bedrock(prompt)
        remediation = parse_json_response(ai_response)

        db.execute("UPDATE incidents SET remediation = ?, severity = ? WHERE id = ?",
                   (json.dumps(remediation), remediation.get("severity", "medium"), incident_id))
        db.commit()

        update_step(db, incident_id, "remediation", "done", output=remediation)
    except Exception as e:
        remediation = {"error": str(e), "summary": "Remediation failed"}
        update_step(db, incident_id, "remediation", "failed", output=remediation)
        update_incident_status(db, incident_id, "failed")
        db.close()
        return get_incident(incident_id)

    # Step 4: Execution (smart action routing)
    update_step(db, incident_id, "execution", "running")
    update_incident_status(db, incident_id, "executing")

    action_type = remediation.get("action_type", "code_fix")

    # Always create a GitHub Issue for tracking
    issue_title = diagnosis.get("title", "Incident")
    issue_body = (
        f"## Incident Report\n\n"
        f"**Description:** {incident['description']}\n\n"
        f"**Root Cause:** {diagnosis.get('root_cause', 'Under investigation')}\n\n"
        f"**Severity:** {remediation.get('severity', 'medium')}\n\n"
        f"**Action Type:** `{action_type}`\n\n"
        f"## Suggested Fix\n\n"
        f"{remediation.get('suggested_fix', 'Investigating...')}\n\n"
        f"## Immediate Actions\n\n"
    )
    for action in remediation.get("immediate_actions", []):
        issue_body += f"- {action}\n"

    ticket = create_issue(
        title=issue_title,
        body=issue_body,
        priority=remediation.get("severity", "medium"),
    )
    db.execute("UPDATE incidents SET ticket = ? WHERE id = ?", (json.dumps(ticket), incident_id))
    log_connector_activity(db, incident_id, "github", "issueCreate",
                           "succeeded" if "error" not in ticket else "failed", ticket)

    # Route to the appropriate action based on AI decision
    pr = {}
    aws_action_result = {}

    if action_type == "code_fix":
        # Code bug → Create a PR with the fix
        branch_name = f"fix/incident-{incident_id[:6]}"
        pr_title = f"fix: {diagnosis.get('title', 'incident resolution')}"
        pr_body = (
            f"## Automated Incident Fix\n\n"
            f"Resolves {ticket.get('id', 'incident')}\n\n"
            f"**Root Cause:** {diagnosis.get('root_cause', 'Unknown')}\n\n"
            f"**Suggested Fix:** {remediation.get('suggested_fix', '')}\n\n"
            f"---\n*Generated by Runbook AI Pipeline*"
        )
        pr = create_pull_request(
            title=pr_title,
            body=pr_body,
            branch_name=branch_name,
            files_to_change=remediation.get("files_to_change", []),
            code_fix=remediation.get("code_fix"),
        )
        db.execute("UPDATE incidents SET pull_request = ? WHERE id = ?", (json.dumps(pr), incident_id))
        log_connector_activity(db, incident_id, "github", "draftPullRequest",
                               "succeeded" if "error" not in pr else "failed", pr)

    elif action_type in ("restart_instance", "restart_service", "cleanup_disk", "scale_up", "config_change", "run_command"):
        # Infrastructure action → Execute via AWS connector
        action_params = remediation.get("action_params", {})
        aws_action_result = execute_aws_action(action_type, action_params)

        # Store the AWS action result
        db.execute("UPDATE incidents SET pull_request = ? WHERE id = ?",
                   (json.dumps({"action_type": action_type, "aws_result": aws_action_result}), incident_id))
        log_connector_activity(db, incident_id, "aws", action_type,
                               "succeeded" if aws_action_result.get("success") else "failed",
                               aws_action_result)

    # Log Discord reply activity
    action_summary = aws_action_result.get("message", "") if aws_action_result else f"PR: {pr.get('url', 'N/A')}"
    log_connector_activity(db, incident_id, "discord", "chat.postMessage", "succeeded", {
        "message": f"Incident resolved via {action_type}. {action_summary}. Ticket: {ticket.get('id', 'N/A')}"
    })

    update_step(db, incident_id, "execution", "done")
    db.commit()

    # Step 5: Store in memory
    update_step(db, incident_id, "memory", "running")
    try:
        store_incident_memory(
            incident_id=incident_id,
            description=incident["description"],
            diagnosis=diagnosis,
            remediation=remediation
        )
        update_step(db, incident_id, "memory", "done")
    except Exception:
        update_step(db, incident_id, "memory", "done")  # Non-critical

    # Mark resolved
    update_incident_status(db, incident_id, "resolved")
    db.execute("UPDATE incidents SET resolved_at = ? WHERE id = ?",
               (datetime.utcnow().isoformat(), incident_id))
    db.commit()
    db.close()

    return get_incident(incident_id)


def update_step(db, incident_id: str, step_name: str, status: str, output: dict = None):
    """Update a pipeline step's status."""
    now = datetime.utcnow().isoformat()
    if status == "running":
        db.execute(
            "UPDATE pipeline_steps SET status = ?, started_at = ? WHERE incident_id = ? AND step_name = ?",
            (status, now, incident_id, step_name)
        )
    else:
        params = [status, now]
        set_clause = "status = ?, completed_at = ?"
        if output:
            set_clause += ", output = ?"
            params.append(json.dumps(output))
        params.extend([incident_id, step_name])
        db.execute(
            f"UPDATE pipeline_steps SET {set_clause} WHERE incident_id = ? AND step_name = ?",
            params
        )
    db.commit()


def update_incident_status(db, incident_id: str, status: str):
    db.execute("UPDATE incidents SET status = ? WHERE id = ?", (status, incident_id))
    db.commit()


def log_connector_activity(db, incident_id: str, connector: str, action: str, status: str, details: dict):
    db.execute(
        """INSERT INTO connector_activity (id, incident_id, connector, action, status, details, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4())[:12], incident_id, connector, action, status,
         json.dumps(details), datetime.utcnow().isoformat())
    )
    db.commit()


def format_past_incidents(past_incidents: list) -> str:
    if not past_incidents:
        return "No similar past incidents found."

    sections = []
    for inc in past_incidents[:3]:
        sections.append(f"""
--- Past Incident ---
Summary: {inc.get('summary', 'N/A')}
Root Cause: {inc.get('root_cause', 'N/A')}
Resolution: {inc.get('resolution', 'N/A')}
---""")
    return "\n".join(sections)
