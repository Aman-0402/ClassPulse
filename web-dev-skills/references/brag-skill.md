---
name: reference-brag-skill
description: /brag — Claude Code Agent Skill by latent-spaces that turns a finished project into a shareable launch video via Hyperframes
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:05:37.283Z
---

`/brag` (latent-spaces/brag on GitHub) — Agent Skill (not a UI component library, unlike [[reference-unlumen-ui]] etc.). Turns a just-built project into a short shareable launch video (music, motion, share copy) by reading the project code directly (no live URL/screenshots needed) and handing a brief to Hyperframes, which builds/times/renders the video.

Install: `npx skills add https://github.com/latent-spaces/brag --skill brag` (add `-g` for global install).
Works with any Agent-Skills-compatible tool: Claude Code, opencode, Codex CLI, etc.

Repo: https://github.com/latent-spaces/brag
Docs/SKILL.md: https://github.com/latent-spaces/brag/blob/main/skills/brag/SKILL.md
Site: https://latent-spaces.github.io/brag/

Trigger phrases: "/brag", "let's brag about this", "make a launch video", "turn this into a video".
