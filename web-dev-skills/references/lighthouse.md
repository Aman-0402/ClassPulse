---
name: reference-lighthouse
description: Google Lighthouse — audit tool for page performance/accessibility/SEO; use to verify fast-load goal on website work
metadata:
  node_type: memory
  type: reference
  originSessionId: 5b9c3d94-ef90-4367-8ed4-05922e80e9f8
  modified: 2026-09-26T07:10:22.199Z
---

Lighthouse — Google's open-source automated web page auditing tool. Scores 0-100 on Performance, Accessibility, Best Practices, SEO (and PWA). Run via Chrome DevTools, CLI (`lighthouse <url>`), Node module, or PageSpeed Insights (web).

Run to verify page load speed ("loadfast") when building/editing a website — ties into [[feedback-website-seo-aeo-geo]] (SEO score + Core Web Vitals are directly measured by Lighthouse's Performance/SEO categories).

Docs: https://developer.chrome.com/docs/lighthouse/overview
CLI: `npx lighthouse <url> --view`
