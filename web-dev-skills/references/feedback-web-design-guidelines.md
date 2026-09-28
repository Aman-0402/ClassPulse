---
name: feedback-web-design-guidelines
description: "Apply design-taste skill's rules on every web design task — typography, color, motion, interaction states, anti-slop"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:30:52.684Z
---

Always apply the [[reference-design-taste-skill]] guidelines when building or reviewing any web UI (landing pages, dashboards, components, forms):

- **Typography**: scale ratio ≥1.25 between steps, body line length 65-75ch, max 3 font families, avoid reflex Inter/serif defaults, `text-wrap: balance` on headings.
- **Color**: contrast ≥4.5:1 body / ≥3:1 large text, one locked accent color, no pure black/white, avoid AI-purple-glow and beige/brass reflex palettes.
- **Layout**: 4/8px spacing scale, cards only when elevation is meaningful (never nested), one corner-radius system, semantic z-index tokens (no magic `9999`).
- **Motion**: every animation needs a purpose, <300ms, ease-out only, animate transform/opacity only, mandatory `prefers-reduced-motion` fallback.
- **Interaction**: design all 8 states (default/hover/focus/active/disabled/loading/error/success), labels above inputs, 44px+ touch targets.
- **Copy**: no em dashes, no marketing buzzwords, no placeholder names (Acme/John Doe).
- **Anti-slop test**: if it reads as "AI made this," rework it.
- **Iron law**: never ship the first draft — build → critique → refine → pre-flight → ship.

**Why:** user explicitly asked this be saved as a standing rule after loading the `design-taste` skill.

**How to apply:** treat this as the default lens for any UI work, alongside [[feedback-website-seo-aeo-geo]] for full-page/website builds. Load the actual `design-taste` skill (Skill tool) for full depth (reference files: pre-flight, anti-slop, motion, interaction-states, design-systems) rather than relying on this summary alone when doing real design work.
