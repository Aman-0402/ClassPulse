---
name: reference-screenshot-to-code
description: "screenshot-to-code (abi/screenshot-to-code) — drop a UI screenshot, get generated HTML/React/Vue/Bootstrap/Ionic code via vision model"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:32:04.386Z
---

`screenshot-to-code` (github.com/abi/screenshot-to-code) — most popular open-source image-to-code tool, 72k+ stars. Drop in a screenshot/design image, pick output target (HTML+Tailwind, React+Tailwind, Vue+Tailwind, Bootstrap, Ionic+Tailwind), generates matching code via a vision-capable LLM. Self-hosted: React frontend + FastAPI backend, bring your own OpenAI/Anthropic/Gemini API key (no managed hosting cost).

Repo: https://github.com/abi/screenshot-to-code

Alternatives noted alongside it:
- **v0 by Vercel** — hosted, image-to-code beta, outputs shadcn/ui + Tailwind components directly (best fit if already on shadcn, matches [[reference-21st-dev]] ecosystem).
- **OpenKombai** — local-LLM version, zero API cost/cloud dependency.

**Realistic expectation:** output typically reproduces ~70-80% of layout; still need to add real interaction states (pairs with [[feedback-web-design-guidelines]]'s 8-state requirement), responsiveness, and real data manually.
