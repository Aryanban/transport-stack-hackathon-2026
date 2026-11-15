# Transport Stack Hackathon 2026 — Delhi

> **Official Challenge Platform:** [Where U Elevate Drill](https://whereuelevate.com/drills/transport-stack-hackathon-2026?w_ref=J66P10)  
> **Official Hackathon Portal:** [delhi.transportstack.in/hackathon](https://delhi.transportstack.in/hackathon/)  
> **Data Access Portal:** [delhi.transportstack.in](https://delhi.transportstack.in/)  
> **Organizer Initiative:** Transport Stack — Japan International Cooperation Agency (JICA), Chartr, Centre for Sustainable Mobility (CSM) at IIIT Delhi, and Airawat Research Foundation (ARF) at IIT Kanpur.

---

## 🏆 Key Information

| Attribute | Details |
| :--- | :--- |
| **Prize Pool** | ₹2,75,000 |
| **Team Size** | 2 to 3 members |
| **Eligibility** | Open to students, researchers, startups, and working professionals (India and abroad) |
| **Participation Fee** | Free |
| **Mode** | Online Phases + In-Person Finale at IIIT Delhi |
| **Registration Deadline** | 20 November 2026, 23:59 IST |
| **Finale Date** | 11 December 2026 (Transport Stack Annual Event at IIIT Delhi) |
| **Official Queries Email** | `transportstack.hackathon@gmail.com` / `csm@iiitd.ac.in` |

---

## 🗓️ Hackathon Timeline & Phases

### Phase 1: Prototype Round (Open to All Registered Teams)
- **Duration:** 2 Weeks (through November 2026)
- **Selection:** Teams choose **Problem 1** (Real-time bus traffic model & journey planner) OR **Problem 2** (Crowdedness-aware journey planner).
- **Deliverables Required:**
  1. Proposal & Working Prototype
  2. Source code repository with comprehensive `README`
  3. Short Technical Note (methodology, data joins, traffic/crowding modeling, assumptions)
  4. Short Demo Video (walkthrough)
  > *Note: Mock-only or slide-only submissions do NOT qualify.*

### Phase 2: Building & Mentorship (Shortlisted 10–12 Teams)
- **Duration:** ~2 Weeks (late November to early December 2026)
- **Format:** Weekly 10–15 minute mentor check-ins with CSM / JICA transit specialists.
- **Challenge Scope:** Refine Phase 1 prototypes OR tackle advanced transit challenges:
  - **Problem 3:** City-wide Origin–Destination (OD) matrix extrapolation
  - **Problem 4:** Metro Feeder EV bus route optimization (7 km constraint, charging profiles)
  - **Problem 5:** Metro and bus crowding estimation from month-long AFC gate records

### Grand Finale & Demo Day
- **Date:** 11 December 2026
- **Venue:** IIIT Delhi (Transport Stack Annual Event)
- **Outcome:** Winners announced, prizes awarded, and standout open-source code integrated into the production Delhi Transport Stack!

---

## 🎯 The Five Problem Statements

1. **Problem 1 (Phase 1): Real-time bus traffic model and journey planner**  
   Turn Delhi’s several thousand moving buses into a city-wide dynamic traffic model and build a Google Maps-grade transit journey planner that computes realistic travel times based on time-of-day traffic and live GPS.
2. **Problem 2 (Phase 1): Crowdedness-aware journey planner**  
   Model passenger occupancy and crowdedness levels (seats available, standing, packed) from 4–5 weeks of bus ETM and e-ticketing logs, integrating real-time and predicted crowding into journey recommendations.
3. **Problem 3 (Phase 2): Origin–destination matrix for Delhi public transit**  
   Extrapolate 3–4% sample bus e-ticketing data to total city bus ridership using full metro AFC tap records as an anchor for spatial travel demand.
4. **Problem 4 (Phase 2): Metro feeder bus routes for 500 electric buses**  
   Design last-mile feeder networks for target metro stations under strict constraints: ≤ 7 km route length, road widths > 6 m, traffic-aware schedules, and EV depot charging constraints.
5. **Problem 5 (Phase 2): Metro and bus crowding estimation**  
   Estimate segment-by-segment and directional passenger loads across all Delhi Metro lines and bus corridors from AFC tap-in/tap-out data.

---

## 📊 Judging Criteria

- **Problem Relevance & Technical Depth:** Correct use and sound preprocessing of real transit data (GTFS, GTFS-RT, AFC, ETM).
- **Accuracy & Validation:** Travel time validation against known ground truth / Google Maps; crowding validation against peak vs. off-peak corridor trends.
- **Feasibility & Engineering Quality:** Clean API design, reproducible pipeline, self-hosting capability, clear documentation.
- **Usability & Commuter Impact:** Intuitive user interface or API responses that help daily commuters make informed transit decisions.
