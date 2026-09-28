# Web Dev Skills

Portable Claude Code skills for web dev projects.

## Use
Copy needed skill folder(s) into target project's `.claude/skills/` (project-scoped) or into `~/.claude/skills/` (global, all projects). Claude auto-detects and loads by name via Skill tool.

For website work specifically, feed `prompt.txt` to the agent (or have it read the file) — it's a standing checklist covering design taste, SEO/AEO/GEO, component-library picks, and pre-ship verification, tying together everything in `references/`.

## Contents

### Custom skills (SKILL.md, written for this project)
- `react-frontend/` — React+TS, Wouter, TanStack Query, RHF+zod, Tailwind/shadcn conventions.
- `express-api/` — Express, Passport, Drizzle ORM backend conventions.
- `innolance-lms-fullstack/` — end-to-end DB→API→UI workflow, written for Innolance LMS stack. Edit stack specifics (routing lib, ORM, auth) before reuse on a different project.

### Installed third-party skills (copied as-is, run with full agent permissions — review before use)
- `graphify/` — turns a codebase (+docs/SQL/PDFs) into a queryable knowledge graph. Source: [Graphify-Labs/graphify](https://github.com/safishamsi/graphify).
- `design-taste/` — anti-"AI slop" frontend design engine (typography, color, motion, anti-patterns). Source: [h3nryprod01/design-taste](https://github.com/h3nryprod01/design-taste).
- `brag/` — turns a finished project into a shareable launch video via Hyperframes. Source: [latent-spaces/brag](https://github.com/latent-spaces/brag).

### references/ — notes on tools *not* installed as skills (component libraries, CLIs, standing rules)
- `unlumen-ui.md`, `magic-ui.md`, `smooth-ui.md`, `retro-ui.md`, `aceternity-ui.md`, `animaster-lib.md` — animated React/Tailwind component libraries (shadcn-CLI installable except Animaster).
- `21st-dev.md` — component marketplace/aggregator for the above.
- `awesome-design-md.md` — VoltAgent DESIGN.md brand design-token collections, pairs with `design-taste/`.
- `screenshot-to-code.md` — image → HTML/React/Vue via vision LLM.
- `playwright-cli.md` — token-efficient CLI for agents to drive Playwright (browser verification).
- `lighthouse.md`, `context7.md` — Google page-audit tool; MCP server for current library docs (backend debugging).
- `feedback-seo-aeo-geo.md`, `feedback-web-design-guidelines.md` — standing rules to apply on website/UI work.
- `claude-red.md` — SnailSploit offensive-security skill library (78 SKILL.md files, authorized pentesting/CTF/research only). Not installed here; install is blocked by Claude Code's auto-mode safety classifier and must be run manually (`git clone https://github.com/SnailSploit/claude-red ~/.claude/skills/claude-red`).

## Add new skill
```
mkdir web-dev-skills/<skill-name>
```
Create `SKILL.md` inside with frontmatter:
```
---
name: <skill-name>
description: <when to use this skill, specific>
---
```
Then write conventions/checklist body.
