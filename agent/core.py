from __future__ import annotations
from openai import AsyncOpenAI
from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .memory import Memory
from .skills import SkillRegistry

SYSTEM = """You are Rohan's personal AI agent. Be direct, practical and concise.\nYou can plan multi-step tasks, use registered skills, and coordinate laptop/mobile workers. Never claim an action was completed unless a tool actually completed it. Never expose secrets. Treat destructive, financial, account-security and irreversible actions as approval-required."""

class Agent:
    def __init__(self):
        self.memory = Memory()
        self.skills = SkillRegistry()
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL) if OPENAI_API_KEY else None

    async def chat(self, text: str) -> str:
        self.memory.add("user", text)
        if not self.client:
            reply = "Agent core is installed, but OPENAI_API_KEY is not configured yet."
        else:
            history = self.memory.load()[-20:]
            messages = [{"role":"system","content":SYSTEM + "\nAvailable skills:\n" + self.skills.context()}] + history
            response = await self.client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
            reply = response.choices[0].message.content or "No response."
        self.memory.add("assistant", reply)
        return reply
