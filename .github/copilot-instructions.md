# GitHub Copilot & Workspace Instructions

See `AGENTS.md` for complete architecture, API schemas, and mathematical formulations.

## Critical Instructions:
- **Testing:** Always run `PYTHONPATH=. .venv/bin/pytest tests/test_engine.py -v` before finalizing any PR or commit.
- **Security:** Never expose or commit `.env` or raw `DELHI_GTFS_RT_API_KEY`.
- **UI & Frontend Taste:** Adhere to `.agents/skills/` (frontend-design, emil-design-eng, apple-design, web-design-guidelines, review-animations).
  - Sub-300ms motion budget, GPU-only transforms.
  - Tactile pointerdown `:active` states (`scale: 0.97`).
  - Distinct typography and atmospheric depth over generic AI SaaS card kits.
