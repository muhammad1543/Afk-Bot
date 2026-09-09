# Personal AI Agent

A modular personal AI agent controlled through Discord and connected workers.

## Goals
- Discord-first conversation and task control
- Laptop worker for approved local tasks
- Mobile-friendly control through Discord/web interface
- Modular skills loaded from `skills/`
- GitHub-based skill management
- Persistent memory and task state
- Explicit permission gates for risky actions

## Safety model
The agent must never expose secrets, bypass authentication, disable security controls, or execute destructive/system-changing actions without explicit authorization. Skills should declare their required permissions.

## Skill contract
Every skill should contain:
- `SKILL.md` — purpose, triggers, inputs, outputs, permissions, workflow
- optional `tools/` — implementation
- optional `tests/` — tests

## Initial skill domains
web-research, github, coding, browser-automation, files, documents, media, youtube, social-media, seo, marketing, ecommerce, data-analysis, email, discord, automation, system-tools.

## Architecture
`Discord -> Agent Core -> Planner -> Skill Router -> Skill -> Worker/API -> Result -> Discord`

Workers are deliberately separated from the core so local laptop capabilities can be enabled independently.
