"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "database", "runbook.db")

# AWS Bedrock
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-2-lite-v1:0")

# Discord
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")

# Backend URL (for Discord bot to call)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
