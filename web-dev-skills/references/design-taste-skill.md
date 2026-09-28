---
name: reference-design-taste-skill
description: design-taste — installed Claude Code skill (h3nryprod01/design-taste) for anti-AI-slop frontend design taste
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:31:00.680Z
---

`design-taste` — Claude Code skill installed globally (`~/.agents/skills/design-taste`, symlinked into Claude Code). Source: https://github.com/h3nryprod01/design-taste (merged synthesis of emilkowalski/skill, pbakaus/impeccable, leonxlnx/taste-skill). Security scan at install: Safe / 0 alerts / Low Risk.

Covers typography, color, layout/spacing, motion, interaction states, copy, and an anti-slop ban list, with mode routing (Persuade/Operate/Read/Experience) that sets design-variance/motion-intensity/visual-density dials per surface type. Full rule summary saved in [[feedback-web-design-guidelines]].

Invoke via Skill tool (`design-taste`) before any UI build/redesign/critique task for full reference-file depth (pre-flight checklist, anti-slop catalogue, motion craft, interaction-states, design-systems).
