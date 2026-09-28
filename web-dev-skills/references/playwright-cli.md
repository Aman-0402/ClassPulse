---
name: reference-playwright-cli
description: "playwright-cli (microsoft/playwright-cli) — token-efficient CLI/skill for coding agents to drive Playwright (screenshots, selectors, codegen)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:32:32.627Z
---

`playwright-cli` (github.com/microsoft/playwright-cli, official Microsoft) — CLI wrapper for common Playwright actions: record/generate Playwright code, inspect selectors, take screenshots. Built specifically for coding agents (Claude Code, GitHub Copilot) that want token-efficient, skill-based browser automation instead of loading large MCP tool schemas + verbose accessibility trees into context.

Headless by default (`--headed` to see the browser). Browser profile stays in-memory per session (cookies/storage lost on close) unless `--persistent` saves it to disk.

Repo: https://github.com/microsoft/playwright-cli
Skill file: https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/SKILL.md
Docs: https://playwright.dev/docs/getting-started-cli

Relevant to CLAUDE.md's "start the dev server and use the feature in a browser before reporting UI work complete" convention — this is the lighter-weight alternative to a full Playwright MCP server for that verification step.
