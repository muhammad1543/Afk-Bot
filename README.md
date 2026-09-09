# Personal AI Agent for Discord + Laptop

This repository contains the personal AI agent runtime built for Discord control and a connected Windows laptop worker.

## What is included

- Discord control from phone or laptop
- OpenAI-compatible LLM integration
- Persistent SQLite memory
- Long-term facts and recent conversation context
- Skill definitions under `skills/*/SKILL.md`
- Safe laptop worker over WebSocket
- Workspace file listing, reading and writing
- Approval gate for consequential file-write actions
- GitHub-skill documentation for extending the agent
- Windows one-click setup and launch scripts
- GitHub Actions CI that compiles the Python runtime on pushes and pull requests

GitHub Actions workflows are stored in `.github/workflows`, where GitHub can automatically run build/test checks on repository events. citeturn195516search0turn195516search4

## Windows setup

1. Download/clone this repository to the laptop.
2. Run `setup_windows.bat`.
3. Open `.env` and set:
   - `DISCORD_TOKEN` — your Discord bot token
   - `OPENAI_API_KEY` — your model API key
   - `AGENT_ALLOWED_USERS` — your Discord user ID(s), comma-separated
   - `WORKER_SECRET` — use the same random secret for agent and worker
4. Start `start_agent.bat`.
5. Start `start_worker.bat` in another terminal.

## Discord commands

- `!status` — health/status
- `!skills` — registered action skills
- `!memory` — stored user facts
- `!ping_laptop` — check laptop worker
- `!approve <id>` — approve a pending action
- `!deny <id>` — deny a pending action
- Mention the bot or DM it to send a normal task

## Security

The worker is deliberately restricted to the agent workspace. It does not provide arbitrary shell execution, credential access, security bypasses, or destructive system control. Consequential actions can require explicit approval.

## Extending skills

Add a folder under `skills/` containing `SKILL.md`. The runtime treats these files as declarative skill definitions; downloaded GitHub content is not blindly executed.

The current repository began as `Afk-Bot`; the personal-agent runtime is now isolated in `agent.py`, `worker.py`, `agent/`, and `skills/` so the existing Minecraft bot code can remain in the repository.
