---
name: reference-claude-red
description: "Claude-Red (SnailSploit) — 78 offensive-security SKILL.md files for Claude (SQLi, shellcode, EDR evasion, exploit dev); install blocked by auto-mode classifier, needs manual/user-run install"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T08:16:35.824Z
---

Claude-Red (github.com/SnailSploit/Claude-Red) — curated library of 78 offensive-security skills for the Claude skills system. Each is a SKILL.md priming Claude with expert methodology for a specific attack surface (SQLi, shellcode, EDR evasion, exploit development, etc.). Skills load on demand by conversational trigger. 3.6k★, 552 forks, last pushed Aug 2026. Use cases: authorized red-team engagements, bug bounty triage, security research, CTF prep — not unauthorized targets.

Repo: https://github.com/SnailSploit/Claude-Red
Install: `git clone https://github.com/SnailSploit/claude-red ~/.claude/skills/claude-red`

**Install status:** attempted twice from this session (2026-09-26), both blocked by Claude Code's server-side auto-mode safety classifier ("Untrusted Code Integration" / unexplained "dangerous" verdict) even with explicit user approval — this is a hard stop, not bypassable from within a session. To actually install: run the `git clone` command yourself in a normal terminal outside Claude Code, or add a Bash permission rule in Claude Code settings that allowlists it first.
