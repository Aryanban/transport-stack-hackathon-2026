// The eight scenes, built from the approved style frames (Design canvas "Delhi bus times video style frames").
// Every number is from the project: data/ps1/model.json, data/ps1/validation.json, README, or the recorded app.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Checklist, Headline, Kicker, StampCard } from "./kit/Editorial";
import { AppShot, Mono, Stat, easeDraw, p01 } from "./parts";
import { rel } from "./timeline";
import { C, MONO, SANS, STYLE } from "./theme";

const L = 112; // left margin

/* 1. Hook: same timetable time all day */
export const S1: React.FC = () => {
  const f = useCurrentFrame();
  const route = "M70 50 L120 70 L160 140 L180 230 L200 300 L290 360";
  const draw = p01(f, 20, 60, easeDraw);
  const stops = [[160, 140], [180, 230], [200, 300]];
  return (
    <AbsoluteFill>
      <Kicker text="ISBT Kashmere Gate to Nehru Place, route 425UP" style={{ position: "absolute", left: L, top: 96 }} />
      <Headline text="48 minutes. Always?" mark="Always" at={8} size={132} style={{ position: "absolute", left: L, top: 290, width: 900 }} />
      <p style={{ position: "absolute", left: L, top: 640, width: 780, margin: 0, fontSize: 38, lineHeight: 1.4, color: C.muted, opacity: p01(f, 50, 16) }}>
        The timetable gives the same time at 5 am and at 6 pm.
      </p>
      <div style={{ position: "absolute", left: L, top: 790 }}>
        <StampCard text="At 6 pm: 79 minutes." at={rel("s1", "seventy")} rotate={-2} size={60} />
      </div>
      <svg style={{ position: "absolute", left: 1000, top: 70 }} width={840} height={840} viewBox="0 0 420 420" aria-hidden>
        <defs>
          <mask id="reveal"><path d={route} stroke="#fff" strokeWidth={8} fill="none" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw} /></mask>
        </defs>
        <path d={route} stroke={C.ink} strokeWidth={2} fill="none" strokeDasharray="7 6" mask="url(#reveal)" />
        <circle cx={70} cy={50} r={8} fill={C.bg} stroke={C.ink} strokeWidth={2} opacity={p01(f, 14, 8)} />
        {stops.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={4 * p01(f, 36 + i * 10, 8)} fill={C.ink} />)}
        <circle cx={290} cy={360} r={8 * p01(f, 78, 10)} fill={C.accent} />
        <path d="M330 50 L330 360 M322 50 L338 50 M322 360 L338 360" stroke={C.muted} strokeWidth={1.5} fill="none" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - p01(f, 70, 24, easeDraw)} />
        <text x={92} y={44} fontFamily={MONO} fontSize={12} fill={C.ink} opacity={p01(f, 20, 10)}>ISBT Kashmere Gate</text>
        <text x={226} y={392} fontFamily={MONO} fontSize={12} fill={C.ink} opacity={p01(f, 82, 10)}>Nehru Place</text>
        <text x={340} y={210} fontFamily={MONO} fontSize={12} fill={C.muted} opacity={p01(f, 90, 10)}>17.2 km</text>
      </svg>
    </AbsoluteFill>
  );
};

/* 2. Problem: model ride time by hour vs the timetable */
const BARS: [string, number][] = [["5 am", 31.5], ["8 am", 41.5], ["noon", 62.3], ["6 pm", 78.6], ["10 pm", 47.6]];
export const S2: React.FC = () => {
  const f = useCurrentFrame();
  const top = 200, height = 660, base = top + height, px = 7.634; // px per minute: 78.6 min fills 600 px
  const tt = base - 48.3 * px;
  return (
    <AbsoluteFill>
      <Kicker text="Same trip, time on the bus, Tuesday 24 November" style={{ position: "absolute", left: L, top: 96 }} />
      <Headline text="Real buses disagree." mark="disagree" at={8} size={128} style={{ position: "absolute", left: L, top: 300, width: 760 }} />
      <div style={{ position: "absolute", left: 940, right: L, top: base, borderTop: `3px solid ${C.ink}`, transform: `scaleX(${p01(f, 4, 20)})`, transformOrigin: "left" }} />
      <div style={{ position: "absolute", left: 920, right: 92, top: tt, borderTop: `3px dashed ${C.timetable}`, opacity: p01(f, 6, 12) }} />
      <Mono style={{ position: "absolute", left: 940, top: tt - 40, opacity: p01(f, 10, 12) }}>timetable: 48.3, all day</Mono>
      <div style={{ position: "absolute", left: 1000, right: 160, top, height, display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", columnGap: 48, alignItems: "end" }}>
        {BARS.map(([label, v], i) => {
          const g = p01(f, rel("s2", "same") + i * 7, 26);
          const peak = i === 3 && f >= rel("s2", "eighty") - 6;
          return (
            <div key={label} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 34, fontWeight: 800, color: peak ? C.accent : C.ink, opacity: g, fontVariantNumeric: "tabular-nums" }}>{(v * g).toFixed(1)}</span>
              <div style={{ width: "100%", height: v * px * g, boxSizing: "border-box", border: peak ? "none" : `3px solid ${C.ink}`, borderBottom: "none", background: peak ? C.accent : "transparent" }} />
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 1000, right: 160, top: base + 18, display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", columnGap: 48, textAlign: "center" }}>
        {BARS.map(([label]) => <Mono key={label} style={{ fontSize: 22 }}>{label}</Mono>)}
      </div>
    </AbsoluteFill>
  );
};

/* 3. Data: a month of GPS */
const DOTS = (() => {
  let s = 7;
  const r = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  return Array.from({ length: 520 }, () => {
    const road = Math.floor(r() * 6), t = r();
    const x = road < 3 ? t * 840 : [160, 420, 660][road - 3] + (r() - 0.5) * 48 + t * 40;
    const y = road < 3 ? [120, 300, 480][road] + (r() - 0.5) * 40 + t * 48 : t * 600;
    return { x, y, dark: r() < 0.15 };
  });
})();
export const S3: React.FC = () => {
  const f = useCurrentFrame();
  const plane = p01(f, 6, 30);
  return (
    <AbsoluteFill>
      <Kicker text="1 to 31 October 2026, the organisers' GPS archive, 124 GB unpacked" style={{ position: "absolute", left: L, top: 96 }} />
      <Headline text="A month of real GPS." mark="real GPS" at={8} size={128} style={{ position: "absolute", left: L, top: 210, width: 860 }} />
      <div style={{ position: "absolute", left: 1000, top: 110, width: 840, height: 600, transform: `perspective(1800px) rotateX(${24 + (1 - plane) * 20}deg) rotateZ(${-6 * plane}deg)`, border: `3px solid ${C.ink}`, background: C.card, overflow: "hidden", opacity: plane }}>
        {DOTS.map((d, i) => (
          <div key={i} style={{ position: "absolute", left: d.x, top: d.y, width: 8, height: 8, borderRadius: 4, background: d.dark ? C.ink : C.accent, opacity: f > 16 + i * 0.3 ? 1 : 0 }} />
        ))}
      </div>
      <div style={{ position: "absolute", left: L, right: L, top: 772, display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 32 }}>
        <Stat label="clean positions" value={420} unit="M+" at={rel("s3", "four")} />
        <Stat label="buses" value={6689} at={rel("s3", "four") + 8} />
        <Stat label="routes" value={2327} at={rel("s3", "four") + 16} />
        <Stat label="days" value={31} at={rel("s3", "four") + 24} />
      </div>
    </AbsoluteFill>
  );
};

/* 4. Pipeline flowchart: raw GPS to planner */
const STEPS: [string, string][] = [["Raw GPS", "420M points"], ["Snap to road", "route shapes"], ["Time stretches", "39.1M timings"], ["Model", "6.5 MB"], ["Planner", "0.2 s a trip"]];
const SNAPS = [[130, 160, 140, 197], [250, 120, 262, 158], [380, 90, 392, 128], [540, 60, 545, 113], [690, 40, 700, 92]];
export const S4: React.FC = () => {
  const f = useCurrentFrame();
  const active = f < rel("s4", "snapped") ? 0 : f < rel("s4", "timed") ? 1 : 2;
  const curve = p01(f, 20, 40, easeDraw);
    const drop = p01(f, rel("s4", "threw"), 10);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: L, right: L, top: 80, display: "flex", alignItems: "center", gap: 20 }}>
        {STEPS.map(([name, sub], i) => {
          const p = p01(f, 4 + i * 6, 14);
          const on = i === active;
          return (
            <React.Fragment key={name}>
              {i > 0 && <span style={{ fontSize: 40, fontWeight: 800, opacity: p }}>→</span>}
              <div style={{ flex: "1 1 0", padding: "16px 22px", background: on ? C.ink : C.card, color: on ? "#FFFFFF" : C.ink, border: `3px solid ${C.ink}`, display: "flex", flexDirection: "column", gap: 4, opacity: p, transform: `translateY(${(1 - p) * 16}px)` }}>
                <span style={{ fontSize: 30, fontWeight: 800 }}>{name}</span>
                <Mono style={{ fontSize: 20, color: on ? C.line : C.muted }}>{sub}</Mono>
              </div>
            </React.Fragment>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: L, right: L, top: 240, height: 600, background: C.card, border: `3px solid ${C.ink}` }}>
        <svg width="100%" height="100%" viewBox="0 0 846 297" aria-hidden>
          <path d="M40 220 C 200 200, 300 120, 460 130 S 700 90, 810 60" stroke={C.accent} strokeWidth={2} fill="none" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - curve} />
          {SNAPS.map(([x1, y1, x2, y2], i) => {
            const a = p01(f, 30 + i * 4, 10);
            const s = p01(f, rel("s4", "snapped") + 4 + i * 5, 20);
            return (
              <g key={i} opacity={a}>
                <path d={`M${x1} ${y1} L${x2} ${y2}`} stroke={C.timetable} strokeWidth={1.5} strokeDasharray="4 4" opacity={s} />
                <circle cx={x2} cy={y2} r={6} fill="#FFFFFF" stroke={C.accent} strokeWidth={2.5} opacity={s} />
                <circle cx={x1 + (x2 - x1) * s} cy={y1 + (y2 - y1) * s} r={5} fill={C.ink} />
              </g>
            );
          })}
          <path d="M470 250 L520 200 M520 250 L470 200" stroke={C.drop} strokeWidth={2} opacity={drop} />
        </svg>
      </div>
      <Mono style={{ position: "absolute", left: 160, top: 268, opacity: p01(f, 30, 10) }}>GPS point, snapped onto route 425UP</Mono>
      <Mono style={{ position: "absolute", left: 1180, top: 760, color: C.drop, opacity: drop }}>dropped: 60 m off the road, or over 90 km/h</Mono>
      <div style={{ position: "absolute", left: 420, top: 640 }}>
        <StampCard text="39.1 million timed stretches." at={rel("s4", "thirty")} rotate={-1.5} size={56} />
      </div>
    </AbsoluteFill>
  );
};

/* 5. The model: four learned factors, and the city's hourly pattern */
const HOURLY = [0.7, 0.64, 0.62, 0.63, 0.68, 0.73, 0.77, 0.85, 0.93, 1.02, 1.02, 1.04, 1.06, 1.07, 1.06, 1.06, 1.08, 1.14, 1.26, 1.21, 1.1, 0.98, 0.86, 0.77];
const FACTORS: [string, string][] = [["Distance", "13 s + 135 s per km"], ["Hour of day", "weekday or weekend"], ["This road", "13,525 stretches"], ["Its rush hour", "205,974 corrections"]];
export const S5: React.FC = () => {
  const f = useCurrentFrame();
  // highlight follows the voice: distance, the hour, each road, its rush hour
  const active = f < rel("s5", "distance") ? -1 : f < rel("s5", "hour") ? 0 : f < rel("s5", "road") ? 1 : f < rel("s5", "rush") ? 2 : 3;
  const h = rel("s5", "hour");
  const x = (h: number) => 40 + h * (766 / 23);
  const y = (v: number) => 150 - (v - 0.5) * 160;
  const d = HOURLY.map((v, h) => `${h ? "L" : "M"}${x(h).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const draw = p01(f, h, 54, easeDraw);
  return (
    <AbsoluteFill>
      <Kicker text="The model: statistical machine learning, every factor learned from the timings" style={{ position: "absolute", left: L, top: 96 }} />
      <Headline text="Four things it learns." mark="learns" at={8} size={112} style={{ position: "absolute", left: L, top: 160 }} />
      <div style={{ position: "absolute", left: L, right: L, top: 350, display: "flex", alignItems: "stretch", gap: 20 }}>
        {FACTORS.map(([name, sub], i) => {
          const p = p01(f, 14 + i * 5, 14);
          const on = i === active;
          return (
            <React.Fragment key={name}>
              {i > 0 && <span style={{ alignSelf: "center", fontSize: 44, fontWeight: 800, opacity: p }}>×</span>}
              <div style={{ flex: "1 1 0", padding: "22px 26px", background: on ? C.ink : C.card, color: on ? "#FFFFFF" : C.ink, border: `3px solid ${C.ink}`, display: "flex", flexDirection: "column", gap: 6, opacity: p, transform: `translateY(${(1 - p) * 16}px) scale(${on ? 1.03 : 1})` }}>
                <span style={{ fontSize: 32, fontWeight: 800 }}>{name}</span>
                <Mono style={{ fontSize: 22, color: on ? C.line : C.muted }}>{sub}</Mono>
              </div>
            </React.Fragment>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: L, right: L, top: 540, height: 340, background: C.card, border: `3px solid ${C.ink}`, opacity: p01(f, h - 10, 12) }}>
        <svg width="100%" height="100%" viewBox="0 0 846 167" aria-hidden>
          <path d={d} stroke={C.accent} strokeWidth={2} fill="none" strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - draw} />
          <path d={`M40 ${y(1)} H 806`} stroke={C.timetable} strokeWidth={1} strokeDasharray="4 4" />
        </svg>
        <div style={{ position: "absolute", left: `${(x(18) / 846) * 100}%`, top: `${(y(1.26) / 167) * 100}%`, width: 18, height: 18, marginLeft: -9, marginTop: -9, borderRadius: 9, background: C.accent, transform: `scale(${p01(f, h + 50, 10)})` }} />
      </div>
      <Mono style={{ position: "absolute", left: 140, top: 556, opacity: p01(f, h - 6, 12) }}>city traffic factor by hour, learned from October</Mono>
      <Mono style={{ position: "absolute", left: 1470, top: 600, color: C.accent, fontWeight: 500, opacity: p01(f, h + 54, 10) }}>6 pm: 1.26</Mono>
      <Mono style={{ position: "absolute", left: 240, top: 826, color: C.accent, opacity: p01(f, h + 16, 10) }}>2 am: 0.62</Mono>
    </AbsoluteFill>
  );
};

/* 6. Proof: held-out week */
export const S6: React.FC = () => {
  const f = useCurrentFrame();
  const res = rel("s6", "forty");
  const err = 3.45 * p01(f, res - 6, 30);
  return (
    <AbsoluteFill>
      <Kicker text="Trained on 1 to 24 October, tested on 50,000 real trips from 25 to 31 October" style={{ position: "absolute", left: L, top: 96 }} />
      <div style={{ position: "absolute", left: L, top: 192, width: 660, display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 10 }}>
        {Array.from({ length: 31 }, (_, i) => {
          const test = i >= 24;
          const on = test ? p01(f, rel("s6", "tested") + (i - 24) * 3, 8) : 0;
          return (
            <div key={i} style={{ height: 60, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontSize: 22, boxSizing: "border-box", border: `3px solid ${test ? C.accent : C.line}`, background: on > 0.5 ? C.accent : C.card, color: on > 0.5 ? "#FFFFFF" : C.muted, opacity: p01(f, 4 + i, 6) }}>
              {i + 1}
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 120, top: 660 }}>
        <StampCard text="A week it never saw." at={rel("s6", "never")} rotate={-1.5} size={56} />
      </div>
      <div style={{ position: "absolute", left: 880, right: L, top: 184, padding: "48px 56px", background: C.card, border: `3px solid ${C.ink}`, display: "flex", flexDirection: "column", gap: 26, opacity: p01(f, res - 12, 12) }}>
        <span style={{ fontFamily: SANS, fontSize: 96, fontWeight: 800, lineHeight: 1, letterSpacing: STYLE.type.tracking }}>{err.toFixed(2)} <span style={{ fontSize: 44 }}>min</span></span>
        <Mono>average error per trip. Timetable: 5.72 min</Mono>
        <div style={{ height: 12, background: C.track }}>
          <div style={{ width: `${60.3 * p01(f, res - 6, 30)}%`, height: 12, background: C.accent }} />
        </div>
        <div style={{ fontSize: 34 }}>
          <Checklist items={["40% less error than the timetable", "73% of trips within ±20% (timetable 42%)", "Better at 24 of 24 hours", "Median error 1.57 min (timetable 3.51)"]} at={res + 14} size={34} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* 7. The real app: one recorded session, cut to the voice line by line */
export const S7: React.FC = () => {
  const f = useCurrentFrame();
  const w = (x: string, n = 0) => rel("s7", x, n);
  const shots = [
    { from: 0, to: w("six"), clipAt: 6.2 },
    { from: w("six"), to: w("tap"), clipAt: 8.6, z: 2.0, fx: 0, fy: 0.8 },
    { from: w("tap"), to: w("every"), clipAt: 20.1, z: 1.6, fx: 0, fy: 0.3 },
    { from: w("every"), to: w("live"), clipAt: 29.1 },
    { from: w("live"), to: w("and", 2), clipAt: 35.8, z: 1.2, fx: 0.6, fy: 0.5 },
    { from: w("and", 2), to: 9999, clipAt: 44.0, z: 1.5, fx: 0.6, fy: 0.3 },
  ];
  const cards = p01(f, w("seventy"), 12) * (f < w("tap") ? 1 : 0);
  const cards5 = p01(f, w("thirty"), 12) * (f < w("every") ? 1 : 0);
  return (
    <AbsoluteFill>
      <AppShot shots={shots} x={120} y={60} w={2000} at={0} />
      <div style={{ position: "absolute", left: 1000, top: 560, display: "flex", gap: 20, opacity: cards, transform: `translateY(${(1 - cards) * 24}px)` }}>
        {[["on the bus, 6 pm", "79 min", C.accent], ["fare", "₹15", C.ink]].map(([k, v, col]) => (
          <div key={k} style={{ padding: "20px 28px", background: C.card, border: `3px solid ${C.ink}`, display: "flex", flexDirection: "column", gap: 4 }}>
            <Mono style={{ fontSize: 20 }}>{k}</Mono>
            <span style={{ fontSize: 52, fontWeight: 800, color: col }}>{v}</span>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 1000, top: 560, display: "flex", gap: 20, opacity: cards5, transform: `translateY(${(1 - cards5) * 24}px)` }}>
        {[["on the bus, 5 am", "32 min", C.accent]].map(([k, v, col]) => (
          <div key={k} style={{ padding: "20px 28px", background: C.card, border: `3px solid ${C.ink}`, display: "flex", flexDirection: "column", gap: 4 }}>
            <Mono style={{ fontSize: 20 }}>{k}</Mono>
            <span style={{ fontSize: 52, fontWeight: 800, color: col }}>{v}</span>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 96, height: 184, padding: `0 ${L}px`, display: "flex", alignItems: "center", background: C.bg }}>
        <Headline text="Plan a trip. See the real time." mark="real time" at={14} size={88} />
      </div>
    </AbsoluteFill>
  );
};

/* 8. Close */
export const S8: React.FC = () => {
  const f = useCurrentFrame();
  const a = p01(f, 6, 16), b = p01(f, 18, 16), c = p01(f, 30, 16);
  const rise = (p: number) => ({ opacity: p, transform: `translateY(${(1 - p) * 24}px)` });
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 460, top: 290, display: "flex", alignItems: "center", gap: 36, ...rise(a) }}>
        <svg width={128} height={128} viewBox="0 0 64 64" aria-hidden>
          <rect x="10" y="8" width="44" height="40" rx="8" fill="none" stroke={C.ink} strokeWidth="4" />
          <path d="M10 30 H54 M18 18 H46" stroke={C.ink} strokeWidth="4" />
          <circle cx="20" cy="40" r="3" fill={C.ink} /><circle cx="44" cy="40" r="3" fill={C.ink} />
          <path d="M18 48 V56 M46 48 V56" stroke={C.ink} strokeWidth="4" strokeLinecap="round" />
        </svg>
        <span style={{ fontSize: 108, fontWeight: 800, letterSpacing: STYLE.type.tracking }}>Delhi bus times</span>
      </div>
      <div style={{ position: "absolute", left: 460, top: 496, display: "flex", alignItems: "center", gap: 36, ...rise(b) }}>
        <span style={{ padding: "20px 36px", background: C.accent, color: "#FFFFFF", fontSize: 36, fontWeight: 800 }}>Run it on your laptop</span>
        <span style={{ fontFamily: MONO, fontSize: 32 }}>github.com/Aryanban/transport-stack-hackathon-2026</span>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 690, display: "flex", flexDirection: "column", alignItems: "center", gap: 14, textAlign: "center", ...rise(c) }}>
        <span style={{ fontSize: 32, fontWeight: 800 }}>Built for the Transport Stack Hackathon 2026, Problem 1</span>
        <Mono style={{ fontSize: 22 }}>Data: Delhi Transport Stack GTFS, GTFS-RT and the October 2026 bus GPS archive</Mono>
        <Mono style={{ fontSize: 22 }}>Voice: Microsoft neural voice. Map: MapLibre, OpenFreeMap, OpenStreetMap contributors</Mono>
      </div>
    </AbsoluteFill>
  );
};

