import discord
from discord.ext import commands
from agent.core import Agent
from agent.config import DISCORD_TOKEN, ALLOWED_USERS

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
agent = Agent()

def allowed(user_id):
    return not ALLOWED_USERS or str(user_id) in ALLOWED_USERS

@bot.event
async def on_ready():
    print(f"Agent online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot or not allowed(message.author.id): return
    if bot.user and bot.user in message.mentions:
        text = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if text:
            async with message.channel.typing():
                reply = await agent.chat(text)
            await message.reply(reply[:1900])
    await bot.process_commands(message)

@bot.command()
async def skills(ctx):
    if not allowed(ctx.author.id): return
    items = agent.skills.list()
    await ctx.send("Available skills:\n" + "\n".join(f"• {s.name}" for s in items) if items else "No skills installed yet.")

@bot.command()
async def reloadskills(ctx):
    if not allowed(ctx.author.id): return
    agent.skills.reload()
    await ctx.send(f"Reloaded {len(agent.skills.skills)} skills.")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and configure it.")
    bot.run(DISCORD_TOKEN)
