# AGENTS.md — Autonomous AI Agent Operating Manual
> **For Autonomous AI Coding Agents, IDE Extensions, Multi-Agent Swarms & Codex/ChatGPT**  
> Compatible with: **OpenAI Codex**, **ChatGPT**, **Cursor**, **Windsurf**, **Claude Code**, **Antigravity**, **Cline**, **GitHub Copilot Workspace**, and **Aider**.

---

## ⚡ 1. Repository Essence & Architecture

**Delhi bus times** is our submission for **Problem 1 (real-time bus traffic model and journey planner)**:
a journey planner whose travel times come from a model learned from a month of Delhi bus GPS (the
organisers' October 2026 archive plus our own GTFS-RT log), adjusted live from the GTFS-RT feed.
Crowding (Problem 2) is not built yet: October ticket data is published but not loaded.

**Real data only.** Never add generated, simulated or hand-invented data, and never present a
fallback as live. With no data, show nothing and say so.

### Directory Layout
```
src/ps1/               network.py (GTFS to routes), matcher.py (GPS to stretch timings), model.py
                       (travel-time model), validation.py, live.py (GTFS-RT layer), planner.py,
                       metro.py (metro stations for map context), api.py (FastAPI), web/ (planner UI),
                       october.py (October GPS archive to stretch timings, one day at a time)
src/gtfs_rt_client.py  live GTFS-RT client, live data only
scripts/log_gtfs_rt.py logs the live feed to data/gps_log/
data/delhi_buses_gtfs/ official static GTFS (stop_times.txt.gz)
data/ps1/              model.json, validation.json, google_benchmark.csv
data/raw/              October archive and per-day stretch timings (not in git)
tests/test_ps1.py      test suite
```

---

## 🛠️ 2. Environment Setup & Execution

```bash
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. .venv/bin/pytest tests/ -q                         # run before completing any task
PYTHONPATH=. .venv/bin/uvicorn src.ps1.api:app --port 8020       # planner at http://127.0.0.1:8020/
python -m src.ps1.october && python -m src.ps1.model && python -m src.ps1.validation  # rebuild model
```

---

## 🎨 3. Design & Taste Stack Protocol (Anti-Slop Standard)

Whenever generating, styling, or reviewing frontend interfaces (Leaflet maps, journey planners, transit cards, vehicle speed telemetry, or crowdedness badges), **agents MUST strictly adhere to the skills in `.agents/skills/`**:

### The 5 Core Craft Disciplines

| Skill | Path | Core Mandate |
| :--- | :--- | :--- |
| **`frontend-design`** | [`.agents/skills/frontend-design/`](file:///Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/.agents/skills/frontend-design/) | **Reject AI Slop Tells:** Ban generic purple/violet gradients, identical rounded SaaS cards, and boring Inter/Roboto fonts. Commit to distinct typography (e.g. Space Grotesk, Syne, Outfit, Cabinet Grotesk paired with JetBrains Mono) and atmospheric depth. |
| **`emil-design-eng`** | [`.agents/skills/emil-design-eng/`](file:///Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/.agents/skills/emil-design-eng/) | **Tactile Feedback & Polish:** Zero tap latency. Provide instant visual confirmation on `pointerdown` (`transform: scale(0.97)` on `:active`). Respect optical balance, avoid layout shifts on state change, and craft deliberate toasts/modals. |
| **`apple-design`** | [`.agents/skills/apple-design/`](file:///Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/.agents/skills/apple-design/) | **Fluid Interfaces & Springs:** 1:1 direct manipulation. Drawers, sheets, and sliders track pointer movement with zero lag. Dismissals inherit gesture velocity. Transitions must be interruptible—never lock user input. |
| **`web-design-guidelines`** | [`.agents/skills/web-design-guidelines/`](file:///Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/.agents/skills/web-design-guidelines/) | **Ergonomics & Accessibility:** Strict compliance with 44×44px minimum touch targets, WCAG AA contrast (≥ 4.5:1), keyboard focus rings, and line lengths capped under 80 characters. |
| **`review-animations`** | [`.agents/skills/review-animations/`](file:///Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/.agents/skills/review-animations/) | **Ruthless Motion Budget:** Animation budget is strictly < 300ms (150–250ms sweet spot). Never animate frequent utility actions (filtering, searching, refreshing). Always set `transform-origin` to the user's trigger point. GPU-only: strictly animate `transform` and `opacity`. |

---

## 🤖 4. REST API

See `/docs` on the running server and the API table in `README.md`. Main endpoints: `/journeys`,
`/journeys/day`, `/stops`, `/stops/{id}/departures`, `/routes`, `/routes/{id}`, `/traffic/stretches`,
`/live/vehicles`, `/validation`.

---

## 🔒 5. Security & Sensitive Credentials

1. The GTFS-RT key lives in the gitignored `.env` as `DTS_API_KEY`. Never print, log or commit it.
2. Without a key or network, the live layer returns nothing and the planner falls back to the learned
   model. It never invents positions.

---

## 📐 6. Developer Guidelines

1. Make the smallest complete change. Do not add dependencies without need.
2. Every number shown to users must come from real data or say where it comes from.
3. Run the tests before marking work complete.
