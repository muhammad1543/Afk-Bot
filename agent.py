import asyncio
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import AsyncOpenAI
import websockets

from agent.skill_loader import SkillLoader

load_dotenv()

ROOT = Path(__file__).resolve().parent
WORKSPACE = (ROOT / os.getenv("AGENT_WORKSPACE", "workspace")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)
DB = WORKSPACE / "memory.sqlite3"
REQUIRE_APPROVAL = os.getenv("AGENT_REQUIRE_APPROVAL", "true").lower() == "true"
ALLOWED_USERS = {x.strip() for x in os.getenv("AGENT_ALLOWED_USERS", "").split(",") if x.strip()}
WORKER_SECRET = os.getenv("WORKER_SECRET", "change-this-secret")
WORKER_HOST = os.getenv("WORKER_HOST", "127.0.0.1")
WORKER_PORT = int(os.getenv("WORKER_PORT", "8765"))
SKILL_ROOT = ROOT / "skills"

SYSTEM_PROMPT = """You are a modular personal AI agent controlled through Discord.
Be practical and action-oriented. Never claim a real-world action happened unless a tool returned success.
Use registered skills for actions. Do not reveal secrets. Publishing, financial actions, account/security changes,
deleting data, mass messaging and other consequential actions require explicit user approval.
When a user asks for a task, return JSON only with keys: reply, action, args.
Allowed action names are listed in the action catalog. Use action null for a normal answer.
"""


class Memory:
    def __init__(self, path: Path):
        self.path = path
        with sqlite3.connect(path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,user TEXT,role TEXT,content TEXT,ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            c.execute("CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,user TEXT,request TEXT,status TEXT,result TEXT,ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
            c.execute("CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY AUTOINCREMENT,user TEXT,fact TEXT,ts DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def add(self, user: str, role: str, content: str):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO messages(user,role,content) VALUES(?,?,?)", (user, role, content))

    def recent(self, user: str, limit: int = 16):
        with sqlite3.connect(self.path) as c:
            rows = c.execute("SELECT role,content FROM messages WHERE user=? ORDER BY id DESC LIMIT ?", (user, limit)).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def remember(self, user: str, fact: str):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO facts(user,fact) VALUES(?,?)", (user, fact))

    def facts(self, user: str, limit: int = 20):
        with sqlite3.connect(self.path) as c:
            return [r[0] for r in c.execute("SELECT fact FROM facts WHERE user=? ORDER BY id DESC LIMIT ?", (user, limit)).fetchall()]


class WorkerBridge:
    def __init__(self):
        self.websocket = None
        self.pending: dict[str, asyncio.Future] = {}

    @property
    def online(self):
        return self.websocket is not None

    async def handler(self, ws):
        try:
            first = json.loads(await ws.recv())
            if first.get("type") != "hello" or first.get("secret") != WORKER_SECRET:
                await ws.close(code=1008, reason="Unauthorized")
                return
            self.websocket = ws
            await ws.send(json.dumps({"type": "hello_ok"}))
            async for message in ws:
                data = json.loads(message)
                request_id = data.get("request_id")
                if request_id and request_id in self.pending:
                    fut = self.pending.pop(request_id)
                    if not fut.done():
                        fut.set_result(data)
        finally:
            if self.websocket is ws:
                self.websocket = None

    async def request(self, action: str, args: dict[str, Any], timeout: int = 60):
        if not self.websocket:
            return {"ok": False, "error": "Laptop worker is offline."}
        rid = uuid.uuid4().hex
        fut = asyncio.get_running_loop().create_future()
        self.pending[rid] = fut
        await self.websocket.send(json.dumps({"type": "task", "request_id": rid, "action": action, "args": args}))
        try:
            return await asyncio.wait_for(fut, timeout)
        except Exception as exc:
            self.pending.pop(rid, None)
            return {"ok": False, "error": str(exc)}


class Agent:
    def __init__(self):
        self.memory = Memory(DB)
        self.worker = WorkerBridge()
        self.loader = SkillLoader(SKILL_ROOT)
        key = os.getenv("OPENAI_API_KEY", "").strip()
        self.llm = AsyncOpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")) if key else None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.pending_approvals: dict[str, tuple[str, str, dict[str, Any]]] = {}
        self.skills = {
            "list_files": "List files in the local workspace",
            "read_file": "Read a text file from the local workspace",
            "write_file": "Create or replace a text file in the local workspace",
            "remember": "Store a user fact in long-term memory",
            "ping_laptop": "Check whether the laptop worker is connected",
            "fetch_url": "Fetch a public web URL through the connected laptop worker",
        }

    def allowed(self, user_id: str) -> bool:
        return not ALLOWED_USERS or user_id in ALLOWED_USERS

    def skill_report(self) -> str:
        defs = self.loader.list_definitions()
        names = [x["name"] for x in defs]
        return f"Action skills: {len(self.skills)} | SKILL.md definitions: {len(names)}\n" + (", ".join(names) if names else "(none)")

    async def execute(self, action: str, args: dict[str, Any], user: str):
        if action == "remember":
            fact = str(args.get("fact", "")).strip()
            if not fact:
                return "Missing fact."
            self.memory.remember(user, fact)
            return "Remembered in long-term memory."
        if action == "ping_laptop":
            result = await self.worker.request("ping", {})
            return "Laptop worker online." if result.get("ok") else f"Laptop worker: {result.get('error', 'offline')}"
        if action == "list_files":
            result = await self.worker.request("list_files", {})
            return result.get("result") if result.get("ok") else result.get("error", "No result.")
        if action == "read_file":
            result = await self.worker.request("read_file", {"path": args.get("path", "")})
            return result.get("result") if result.get("ok") else result.get("error", "No result.")
        if action == "write_file":
            result = await self.worker.request("write_file", {"path": args.get("path", ""), "content": args.get("content", "")})
            return result.get("result") or result.get("error", "No result.")
        if action == "fetch_url":
            result = await self.worker.request("fetch_url", {"url": args.get("url", "")})
            return result.get("result") if result.get("ok") else result.get("error", "No result.")
        return "Unknown action."

    async def ask(self, user: str, text: str) -> str:
        self.memory.add(user, "user", text)
        if not self.llm:
            reply = "AI model not configured. Add OPENAI_API_KEY to .env, then restart the agent.\n\nAvailable commands: !status, !skills, !memory, !ping_laptop"
            self.memory.add(user, "assistant", reply)
            return reply

        action_catalog = "\n".join(f"- {name}: {desc}" for name, desc in self.skills.items())
        definition_catalog = self.loader.catalog()
        facts = "\n".join(f"- {x}" for x in self.memory.facts(user)) or "(none)"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nAction catalog:\n" + action_catalog + "\n\nSkill definitions available as guidance:\n" + definition_catalog[:12000] + "\n\nKnown user facts:\n" + facts},
            *self.memory.recent(user),
        ]
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        reply = str(plan.get("reply", "")).strip()
        action = plan.get("action")
        args = plan.get("args") or {}
        if action:
            if action not in self.skills:
                result = f"Action `{action}` is not registered."
            elif REQUIRE_APPROVAL and action in {"write_file"}:
                approval_id = uuid.uuid4().hex[:8]
                self.pending_approvals[approval_id] = (user, action, args)
                result = f"Approval required. Use `!approve {approval_id}` to execute or `!deny {approval_id}`."
            else:
                result = await self.execute(action, args, user)
            reply = (reply + "\n" + str(result)).strip()
        self.memory.add(user, "assistant", reply)
        return reply or "Done."

    async def approve(self, approval_id: str, user: str):
        item = self.pending_approvals.pop(approval_id, None)
        if not item:
            return "Approval ID not found or expired."
        owner, action, args = item
        if owner != user:
            return "That approval does not belong to you."
        return str(await self.execute(action, args, user))

    def deny(self, approval_id: str, user: str):
        item = self.pending_approvals.get(approval_id)
        if not item:
            return "Approval ID not found or expired."
        if item[0] != user:
            return "That approval does not belong to you."
        self.pending_approvals.pop(approval_id, None)
        return "Denied."


agent = Agent()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"AI Agent online as {bot.user}")


@bot.check
async def authorize(ctx):
    return agent.allowed(str(ctx.author.id))


@bot.command()
async def status(ctx):
    await ctx.send(f"🟢 Agent online | Discord ✅ | Memory ✅ | Laptop worker {'✅' if agent.worker.online else '❌'} | {agent.skill_report()}")


@bot.command()
async def skills(ctx):
    await ctx.send(agent.skill_report() + "\n\n" + "\n".join(f"`{name}` — {desc}" for name, desc in agent.skills.items()))


@bot.command()
async def memory(ctx):
    facts = agent.memory.facts(str(ctx.author.id))
    await ctx.send("Your memory:\n" + ("\n".join(f"• {x}" for x in facts) if facts else "(empty)"))


@bot.command()
async def ping_laptop(ctx):
    await ctx.send(await agent.execute("ping_laptop", {}, str(ctx.author.id)))


@bot.command()
async def approve(ctx, approval_id: str):
    await ctx.send(await agent.approve(approval_id, str(ctx.author.id)))


@bot.command()
async def deny(ctx, approval_id: str):
    await ctx.send(agent.deny(approval_id, str(ctx.author.id)))


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    user = str(message.author.id)
    if not agent.allowed(user):
        return
    is_dm = isinstance(message.channel, discord.DMChannel)
    mentioned = bot.user and bot.user.mentioned_in(message)
    if is_dm or mentioned:
        text = message.content
        if bot.user:
            text = text.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if text and not text.startswith("!"):
            async with message.channel.typing():
                try:
                    await message.reply(await agent.ask(user, text), mention_author=False)
                except Exception as exc:
                    await message.reply(f"Agent error: {type(exc).__name__}: {exc}", mention_author=False)
    await bot.process_commands(message)


async def run_server():
    async with websockets.serve(agent.worker.handler, WORKER_HOST, WORKER_PORT):
        print(f"Worker server listening on ws://{WORKER_HOST}:{WORKER_PORT}")
        await asyncio.Future()


async def main():
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN is missing in .env")
    await asyncio.gather(bot.start(token), run_server())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
