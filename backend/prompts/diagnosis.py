"""Prompt for AI-powered incident diagnosis."""


def build_diagnosis_prompt(description: str, past_incidents: str) -> str:
    return f"""You are an expert Site Reliability Engineer investigating a production incident.

INCIDENT REPORT:
{description}

SIMILAR PAST INCIDENTS:
{past_incidents}

Analyze this incident and provide a diagnosis. Consider:
1. What is likely failing based on the symptoms described?
2. What is the probable root cause?
3. What systems/services are affected?
4. How does this compare to past incidents (if any)?

Return as valid JSON:
{{
  "title": "Short incident title (max 10 words)",
  "summary": "One-paragraph diagnosis explaining what is happening",
  "root_cause": "Most likely root cause based on evidence",
  "affected_services": ["list", "of", "affected", "services"],
  "severity": "low or medium or high or critical",
  "confidence": 0-100,
  "evidence": ["specific clues from the report that support this diagnosis"],
  "similar_to_past": true or false,
  "past_incident_match": "Brief note on how this relates to past incidents, or null"
}}
"""
