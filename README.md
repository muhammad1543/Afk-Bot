# Personal AI Agent

This repository now contains a modular Discord-controlled personal AI agent alongside the original AFK Bot code.

## Quick start (Windows)

1. Install Python 3.11+.
2. Clone/download this repository.
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `.venv\\Scripts\\activate`
5. Install: `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `OPENAI_API_KEY`.
7. Enable Discord Developer Portal **Message Content Intent** for the bot.
8. Start: `python agent.py`
9. In Discord, mention the bot and send a request. `!status` and `!skills` are also available.

## Laptop worker

Configure the same `.env` on the laptop and run `python worker.py`. The starter worker intentionally exposes only safe workspace listing. More powerful system/browser/media skills should be explicit and permissioned rather than arbitrary shell execution.

## Skill system

Skills live under `skills/`. Each skill should document permissions, inputs, outputs and failure handling. GitHub can act as the skill registry, but arbitrary repositories/code must not be executed blindly.

## Architecture

`Discord -> Agent Core -> Planner -> Skill Router -> Skill -> Worker/API -> Result -> Discord`

The project includes Discord control, LLM routing, persistent SQLite memory, permission gates, a laptop worker and a GitHub-oriented skill structure. The roadmap covers browser/web research, coding, files/documents, image/video, YouTube, social media, SEO, marketing, ecommerce, Amazon, data analysis, email and automation.