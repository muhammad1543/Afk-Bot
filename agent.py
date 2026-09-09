import asyncio, json, os, sqlite3, uuid
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
WORKSPACE = Path(os.getenv('AGENT_WORKSPACE','./workspace')).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)
DB = WORKSPACE / 'memory.sqlite3'
APPROVAL = os.getenv('AGENT_REQUIRE_APPROVAL','true').lower() == 'true'
ALLOWED = {x.strip() for x in os.getenv('AGENT_ALLOWED_USERS','').split(',') if x.strip()}

SYSTEM = '''You are a modular personal AI agent. Be concise, practical and action-oriented.
You can reason about tasks, but you must use registered tools/skills for real actions.
Never claim an action was executed unless a tool actually returned success.
Never expose secrets. Destructive, financial, account/security, mass messaging, or external publishing actions require explicit approval.
'''

class Memory:
    def __init__(self, db):
        self.db = db
        with sqlite3.connect(db) as c:
            c.execute('CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, user TEXT, role TEXT, content TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)')
            c.execute('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, user TEXT, request TEXT, status TEXT, result TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)')
    def add(self,user,role,content):
        with sqlite3.connect(self.db) as c: c.execute('INSERT INTO messages(user,role,content) VALUES(?,?,?)',(user,role,content))
    def recent(self,user,n=16):
        with sqlite3.connect(self.db) as c: rows=c.execute('SELECT role,content FROM messages WHERE user=? ORDER BY id DESC LIMIT ?',(user,n)).fetchall()
        return [{'role':r,'content':x} for r,x in reversed(rows)]

class Skill:
    def __init__(self,name,description,fn,permission='safe'):
        self.name,self.description,self.fn,self.permission=name,description,fn,permission

class Agent:
    def __init__(self):
        self.memory=Memory(DB)
        self.skills={}
        key=os.getenv('OPENAI_API_KEY')
        self.llm=AsyncOpenAI(api_key=key,base_url=os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1')) if key else None
        self.register(Skill('workspace','List or inspect the agent workspace',self.workspace))
        self.register(Skill('remember','Store a user fact in memory',self.remember))
    def register(self,s): self.skills[s.name]=s
    async def workspace(self,args,user):
        return '\n'.join(str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob('*') if p.is_file()) or '(workspace empty)'
    async def remember(self,args,user):
        fact=str(args.get('fact','')).strip()
        if not fact: return 'Missing fact.'
        self.memory.add(user,'memory',fact); return 'Remembered.'
    async def ask(self,user,text):
        self.memory.add(user,'user',text)
        if not self.llm: return 'LLM is not configured yet. Put OPENAI_API_KEY in .env.'
        catalog='\n'.join(f'- {s.name}: {s.description} (permission={s.permission})' for s in self.skills.values())
        prompt=f'''Registered skills:\n{catalog}\n\nReturn JSON only: {{"reply":"...","skill":null,"args":{{}}}}. Choose a skill only when a real action is needed. User request: {text}'''
        r=await self.llm.chat.completions.create(model=os.getenv('OPENAI_MODEL','gpt-4o-mini'),messages=[{'role':'system','content':SYSTEM},{'role':'system','content':prompt}]+self.memory.recent(user),temperature=0.2)
        raw=r.choices[0].message.content or '{}'
        try: plan=json.loads(raw)
        except Exception: return raw
        skill=plan.get('skill'); args=plan.get('args') or {}
        if skill in self.skills:
            s=self.skills[skill]
            if APPROVAL and s.permission!='safe': return f'Approval required for skill `{skill}`.'
            result=await s.fn(args,user); reply=plan.get('reply','')+'\n'+str(result)
        else: reply=plan.get('reply','')
        self.memory.add(user,'assistant',reply); return reply

agent=Agent()
intents=discord.Intents.default(); intents.message_content=True
bot=commands.Bot(command_prefix='!',intents=intents)

@bot.event
async def on_ready(): print(f'Agent online as {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot: return
    if ALLOWED and str(message.author.id) not in ALLOWED: return
    if bot.user and bot.user.mentioned_in(message):
        text=message.content.replace(f'<@{bot.user.id}>','').replace(f'<@!{bot.user.id}>','').strip()
        if text:
            async with message.channel.typing():
                try: await message.reply(await agent.ask(str(message.author.id),text),mention_author=False)
                except Exception as e: await message.reply(f'Agent error: {type(e).__name__}: {e}',mention_author=False)
    await bot.process_commands(message)

@bot.command()
async def skills(ctx):
    await ctx.send('Skills:\n'+'\n'.join(f'• `{s.name}` — {s.description}' for s in agent.skills.values()))

@bot.command()
async def status(ctx):
    await ctx.send('🟢 Agent core online | Discord connected | Memory online | Skills: '+str(len(agent.skills)))

if __name__=='__main__':
    token=os.getenv('DISCORD_TOKEN')
    if not token: raise SystemExit('DISCORD_TOKEN missing in .env')
    bot.run(token)
