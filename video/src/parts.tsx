// Film-specific parts: progress helper, voice captions, stat cards, and the app shot with a camera.
import React from "react";
import { Easing, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { C, MONO, SANS, STYLE } from "./theme";

const ease = Easing.bezier(0.22, 1, 0.36, 1);
export const easeDraw = Easing.bezier(0.65, 0, 0.35, 1);

/** 0 to 1 from frame `at` over `dur` frames, eased and clamped. */
export const p01 = (frame: number, at: number, dur: number, e = ease) =>
  interpolate(frame, [at, at + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e });

export const VO_LEAD = 12; // frames of quiet before each scene's voice line

/** Caption bar that shows the sentence being spoken. `cues` are [startSec, text] from the voice start. */
export const Captions: React.FC<{ cues: [number, string][] }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const t = (frame - VO_LEAD) / 30;
  let text = cues[0][1];
  for (const [s, line] of cues) if (t >= s) text = line;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 96, padding: "0 112px", display: "flex", alignItems: "center", borderTop: `1px solid ${C.line}`, background: C.bg, fontFamily: SANS, fontSize: 30, fontWeight: 500, color: C.muted }}>
      {text}
    </div>
  );
};

/** Split a line into sentences and time them by length over the voice's duration. */
export const cuesFor = (text: string, seconds: number): [number, string][] => {
  const parts = text.match(/[^.?!]+[.?!]+/g)?.map((s) => s.trim()) ?? [text];
  const total = parts.reduce((a, p) => a + p.length, 0);
  let acc = 0;
  return parts.map((p) => {
    const start = (acc / total) * seconds;
    acc += p.length;
    return [start, p] as [number, string];
  });
};

export const Mono: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <span style={{ fontFamily: MONO, fontSize: 24, color: C.muted, ...style }}>{children}</span>
);

/** A small bordered stat that counts up. Real numbers only. */
export const Stat: React.FC<{ label: string; value: number; decimals?: number; unit?: string; at: number; color?: string; prefix?: string }> = ({
  label, value, decimals = 0, unit = "", at, color = C.ink, prefix = "",
}) => {
  const frame = useCurrentFrame();
  const p = p01(frame, at, 14);
  const n = value * p01(frame, at + 2, 20);
  return (
    <div style={{ padding: "22px 30px", background: C.card, border: `3px solid ${C.ink}`, display: "flex", flexDirection: "column", gap: 6, opacity: p, transform: `translateY(${(1 - p) * 24}px)`, minWidth: 0 }}>
      <Mono style={{ fontSize: 22 }}>{label}</Mono>
      <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: 60, lineHeight: 1.05, letterSpacing: STYLE.type.tracking, color, fontVariantNumeric: "tabular-nums" }}>
        {prefix}{n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}{unit}
      </span>
    </div>
  );
};

export type Shot = { from: number; to: number; clipAt: number; z?: number; fx?: number; fy?: number };

/**
 * The real app in a tilted browser frame that runs off the right edge (Editorial Paper's signature).
 * `shots` cut between moments of one recording (public/clips/app.webm) and move a camera:
 * zoom `z` toward focus point (fx, fy) in the recording's 0..1 space.
 */
export const AppShot: React.FC<{ shots: Shot[]; x: number; y: number; w: number; at?: number; url?: string }> = ({
  shots, x, y, w, at = 0, url = "127.0.0.1:8020",
}) => {
  const frame = useCurrentFrame();
  const h = w * (900 / 1440);
  const bar = 52;
  const enter = p01(frame, at, 40);
  const rotY = -12 + 4 * enter + Math.sin(frame / 70) * 0.5;
  const rotX = 6 - 1.5 * enter;
  const shot = shots.find((s) => frame >= s.from && frame < s.to) ?? shots[shots.length - 1];
  const zp = p01(frame, shot.from, 24);
  const z = 1 + ((shot.z ?? 1) - 1) * zp;
  const fx = shot.fx ?? 0.5, fy = shot.fy ?? 0.5;
  const maxX = (w * (z - 1)) / 2, maxY = (h * (z - 1)) / 2;
  const tx = Math.max(-maxX, Math.min(maxX, (0.5 - fx) * w * (z - 1)));
  const ty = Math.max(-maxY, Math.min(maxY, (0.5 - fy) * h * (z - 1)));
  return (
    <div style={{ position: "absolute", left: x + (1 - enter) * 500, top: y, width: w, height: h + bar, background: C.card, border: `3px solid ${C.ink}`, borderRadius: 8, overflow: "hidden", opacity: Math.min(1, enter * 2), transform: `perspective(2600px) rotateY(${rotY}deg) rotateX(${rotX}deg)`, transformOrigin: "left center", boxShadow: "0 60px 110px -50px rgb(32 33 36 / 0.55), 0 14px 28px -14px rgb(32 33 36 / 0.25)" }}>
      <div style={{ height: bar, display: "flex", alignItems: "center", gap: 10, padding: "0 20px", borderBottom: `1.5px solid ${C.ink}` }}>
        {[0, 1, 2].map((i) => <span key={i} style={{ width: 14, height: 14, borderRadius: 99, border: `2px solid ${C.ink}`, opacity: 0.55 }} />)}
        <span style={{ marginLeft: 18, fontFamily: MONO, fontSize: 22, color: C.muted }}>{url}</span>
      </div>
      <div style={{ width: w, height: h, overflow: "hidden" }}>
        <div style={{ width: w, height: h, transform: `translate(${tx}px, ${ty}px) scale(${z})` }}>
          {/* each shot plays its own moment of the recording from its first frame */}
          <Sequence key={shot.from} from={shot.from} layout="none">
            <OffthreadVideo src={staticFile("clips/app.webm")} startFrom={Math.round(shot.clipAt * 30)} muted style={{ width: w, height: h, display: "block" }} />
          </Sequence>
        </div>
      </div>
    </div>
  );
};
