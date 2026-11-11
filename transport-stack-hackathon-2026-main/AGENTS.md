# AGENTS.md — Autonomous AI Agent Operating Manual
> **For Autonomous AI Coding Agents, IDE Extensions, Multi-Agent Swarms & Codex/ChatGPT**  
> Compatible with: **OpenAI Codex**, **ChatGPT**, **Cursor**, **Windsurf**, **Claude Code**, **Antigravity**, **Cline**, **GitHub Copilot Workspace**, and **Aider**.

---

## ⚡ 1. Repository Essence & Architecture

**Transport Stack Hackathon 2026 — Delhi Transit Engine** is an open-source, high-performance transit routing, congestion estimation, and crowdedness prediction platform for the National Capital Territory (NCT) of Delhi.

It tackles:
- **Problem 1 (Traffic Model & Dynamic Journey Planning):** Fuses Delhi bus fleet GPS telemetry with static GTFS to estimate real-time corridor velocities and predict dynamic travel times that outperform static timetables.
- **Problem 2 (Crowdedness-Aware Journey Planning):** Ingests ticketing logs and pass-holder multipliers (accounting for Delhi's ~35% non-ticketed pink passes) to classify route segments into comfort tiers: *Seats Available*, *Standing Room*, and *Heavily Crowded*, utilizing Hensher-Wardman Value-of-Time (VOT) multipliers.
- **Phase 2 Extensibility:** First/last-mile DMRC feeder bus optimization (Problem 4) and 258×258 AFC Origin-Destination station matrix extrapolation (Problem 3).

### Directory Layout & Key Modules
```
transport-stack-hackathon-2026/
├── .agents/skills/                # Canonical Agent & Design-Engineering Skills (Open Standard)
│   ├── frontend-design/           # Macro aesthetic, typography pairings, atmospheric textures
│   ├── emil-design-eng/           # Micro-interactions, tactile feedback, toast/modal craft
│   ├── apple-design/              # 1:1 direct manipulation, pointer-down responsiveness, spring physics
│   ├── web-design-guidelines/     # Ergonomics, accessibility (WCAG), touch targets, contrast
│   └── review-animations/         # Strict <300ms motion budget, GPU transforms, touch origins
├── .claude/skills/                # Symlinks for Claude Code CLI discovery
├── src/                           # Core Transit Engine & API
│   ├── api.py                     # FastAPI REST application & OpenAPI documentation
│   ├── engine.py                  # Core transit engine orchestrating GTFS, routing, and live telemetry
│   ├── gtfs_loader.py             # GTFS parser (stops, routes, trips, stop_times, calendar)
│   ├── gtfs_rt_client.py          # Real-time GTFS-RT Protobuf client (VehiclePositions.pb)
│   ├── traffic_model.py           # Delhi-specific 24-hr diurnal speed profiles & corridor multipliers
│   ├── crowdedness_model.py       # Passenger occupancy estimator with 1.35x pink-pass multiplier
│   ├── feeder_optimizer.py        # DMRC first/last-mile feeder bus route optimizer
│   └── od_extrapolator.py         # 258x258 DMRC station AFC flow matrix extrapolation
├── data/                          # GTFS static datasets and transit data layers
│   ├── delhi_buses_gtfs/          # Static GTFS for DTC and DIMTS buses
│   └── dmrc_metro_gtfs/           # Static GTFS and station coordinates for Delhi Metro
├── docs/
│   └── RESOURCES.md               # Curated open-source intelligence, API schemas, and mathematical papers
├── tests/                         # Pytest test suite (15 passing integration & unit tests)
│   └── test_engine.py             # Full coverage of routing, traffic, crowdedness, and live APIs
├── pyproject.toml                 # Package definition & dependencies
├── requirements.txt               # Direct pip dependency manifest
├── README.md                      # Human developer documentation & system architecture
└── AGENTS.md                      # This file (AI agent operational instructions)
```

---

## 🛠️ 2. Environment Setup & Execution

All autonomous agents must run within the local Python virtual environment:

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run complete test suite (Always run before completing tasks)
PYTHONPATH=. .venv/bin/pytest tests/test_engine.py -v

# Launch the FastAPI REST server on port 8000
PYTHONPATH=. .venv/bin/uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
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

## 🤖 4. Programmatic REST API & Tool Manifest

Agents interacting with the running server can query or verify endpoints:

| Endpoint | Method | Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | None | System status, GTFS static counts, and live feed health. |
| `/api/v1/journey` | `GET` | `origin_lat`, `origin_lon`, `dest_lat`, `dest_lon`, `departure_time` | Calculates Pareto-optimal multi-modal journey with real-time traffic adjustments. |
| `/api/v1/crowdedness` | `GET` | `route_id`, `hour_of_day` | Returns segment crowdedness estimates and comfort tiers. |
| `/api/v1/live/vehicles` | `GET` | `limit`, `route_id` | Fetches live Delhi bus GPS telemetry from Transport Stack GTFS-RT feed. |
| `/api/v1/live/speeds` | `GET` | None | Returns real-time aggregate fleet speed (km/h) across operational corridors. |
| `/api/v1/od-matrix` | `GET` | `top_n` | Returns top DMRC station origin-destination commuter flows. |
| `/api/v1/feeder-routes` | `GET` | `metro_station_id`, `radius_km` | Generates optimized first/last-mile feeder bus loop suggestions. |

---

## 🔒 5. Security & Sensitive Credentials Protocol

1. **NEVER leak or commit `.env` or raw API keys:**
   - The Transport Stack GTFS-RT API key is managed via `.env` (`DELHI_GTFS_RT_API_KEY`).
   - `.env` is strictly gitignored. Never stage `.env` or print secret values into commit messages or logs.
   - The application securely loads credentials via `os.getenv("DELHI_GTFS_RT_API_KEY")` inside `src/gtfs_rt_client.py`.
2. **Deterministic Fallbacks:**
   - If live API credentials are unset or network is unavailable, `gtfs_rt_client.py` gracefully degrades to simulated historical telemetry so tests and local evaluation never break.

---

## 📐 6. Developer Guidelines for Modifying This Codebase

When writing code or refactoring within this repository:

1. **Surgical, Minimal Changes:**
   - Solve tasks with the smallest complete diff. Do not rewrite functioning modules or add unnecessary bloated dependencies.
2. **Preserve Mathematical Rigor:**
   - Any transit modeling logic must account for Delhi-specific conditions (e.g. peak hour congestion factors, 1.35× pink pass multipliers, and Hensher-Wardman VOT crowding penalties).
3. **Evidence Before Assertions:**
   - Always run the test suite:
     ```bash
     PYTHONPATH=. .venv/bin/pytest tests/test_engine.py -v
     ```
   - Confirm **15/15 tests passing** before marking any work complete.
