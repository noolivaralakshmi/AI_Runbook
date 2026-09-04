"""Amazon Bedrock AI service for incident diagnosis and remediation."""
import json
import boto3
from backend.config import AWS_REGION, BEDROCK_MODEL_ID


def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


def invoke_bedrock(prompt: str, max_tokens: int = 4096) -> str:
    """Invoke Amazon Bedrock using the Converse API."""
    client = get_bedrock_client()

    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
    )

    output = response.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])
    if content:
        return content[0].get("text", "")
    return ""


def parse_json_response(text: str) -> dict:
    """Extract JSON from AI response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to parse AI response", "raw": text}
