from __future__ import annotations
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AGENT_REQUIRE_APPROVAL = os.getenv("AGENT_REQUIRE_APPROVAL", "true").lower() == "true"
WORKER_SECRET = os.getenv("WORKER_SECRET", "")
WORKSPACE = os.getenv("AGENT_WORKSPACE", "./workspace")
ALLOWED_USERS = {x.strip() for x in os.getenv("AGENT_ALLOWED_USERS", "").split(",") if x.strip()}
