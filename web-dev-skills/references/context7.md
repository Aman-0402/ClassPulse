---
name: reference-context7
description: "Context7 — MCP server that fetches current, version-accurate library/framework docs into context; use when debugging backend errors tied to a specific library API"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:10:38.743Z
---

Context7 (by Upstash) — MCP server that pulls up-to-date, version-specific documentation and code examples for a library/framework directly into the conversation, instead of relying on training-data-frozen knowledge. Prevents outdated-API mistakes (deprecated methods, wrong signatures) — a common cause of backend errors when a library version has moved past the model's knowledge cutoff.

**How to apply here:** when a backend error (Express/Drizzle/Passport/etc.) looks like an API-mismatch or "this used to work" issue, pull the current docs for that library via Context7 before guessing at a fix — cheaper than trial-and-error edits.

Repo: https://github.com/upstash/context7
Site: https://context7.com/

Add as MCP server (Claude Code): `claude mcp add context7 -- npx -y @upstash/context7-mcp` (exact command may change — check repo README).
