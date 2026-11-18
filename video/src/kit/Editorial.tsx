// Editorial kit: the parts of the "Editorial Paper" look (Basement Ready, mFCAcvSXj48),
// written against the style library so the same parts render in any style.
// Every part reads the active style from <StyleProvider>; `at` is the entrance frame
// inside the current <Sequence>. Timings in styles.json are frames at 30 fps.

import { getLength } from "@remotion/paths";
import React, { createContext, useContext } from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { drawEaseOf, easeOf, fontsOf, getStyle, type StyleSpec } from "./styles";

const StyleCtx = createContext<StyleSpec>(getStyle("editorial-paper"));
export const StyleProvider: React.FC<{ style: StyleSpec; children: React.ReactNode }> = ({ style, children }) => (
  <StyleCtx.Provider value={style}>{children}</StyleCtx.Provider>
);
export const useStyle = () => useContext(StyleCtx);

/** 0 to 1 from frame `at` over the style's entrance length (times `k`), eased, clamped. */
const useEnter = (at: number, k = 1, draw = false) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = useStyle();
  const dur = Math.max(1, Math.round(s.motion.enter * k * (fps / 30)));
  return interpolate(frame, [at, at + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: draw ? drawEaseOf(s) : easeOf(s),
  });
};
const staggerOf = (s: StyleSpec, fps: number) => Math.round(s.motion.stagger * (fps / 30));

/** The page: flat style background and body font. No grain, no gradient, unless the style asks. */
export const Paper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const s = useStyle();
  return (
    <AbsoluteFill style={{ background: s.colors.bg, color: s.colors.ink, fontFamily: fontsOf(s).body }}>
      {children}
    </AbsoluteFill>
  );
};

/** A small mono line above a headline. Sentence case, no tracking. */
export const Kicker: React.FC<{ text: string; at?: number; style?: React.CSSProperties }> = ({ text, at = 0, style }) => {
  const s = useStyle();
  const p = useEnter(at);
  return (
    <div style={{ fontFamily: fontsOf(s).mono, fontSize: 26, color: s.colors.muted, opacity: p, transform: `translateY(${(1 - p) * 12}px)`, ...style }}>
      {text}
    </div>
  );
};

/** The highlighter block behind one word; wipes in from the left. */
export const Marker: React.FC<{ children: React.ReactNode; at?: number }> = ({ children, at = 0 }) => {
  const s = useStyle();
  const p = useEnter(at, 0.8, true);
  return (
    <span style={{ position: "relative", display: "inline-block", margin: 0 }}>
      <span style={{ position: "absolute", inset: "0.06em -0.1em 0.02em -0.1em", background: s.colors.marker, transform: `scaleX(${p})`, transformOrigin: "left center" }} />
      <span style={{ position: "relative", color: s.colors.onMarker }}>{children}</span>
    </span>
  );
};

/** Huge left-aligned headline; words rise in turn; the `mark` word gets the highlighter. */
export const Headline: React.FC<{ text: string; mark?: string; at?: number; size?: number; style?: React.CSSProperties }> = ({
  text, mark, at = 0, size = 128, style,
}) => {
  const s = useStyle();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const st = staggerOf(s, fps);
  const dur = Math.round(s.motion.enter * (fps / 30));
  // The marked phrase (one or more words) becomes a single token so the highlighter spans it.
  const words: string[] = [];
  const markWords = mark ? mark.split(" ").length : 0;
  const raw = text.split(" ");
  for (let i = 0; i < raw.length; i++) {
    const phrase = raw.slice(i, i + markWords).join(" ");
    if (mark && phrase.replace(/[.,!?]$/, "").toLowerCase() === mark.toLowerCase()) {
      words.push(phrase);
      i += markWords - 1;
    } else words.push(raw[i]);
  }
  return (
    <h1 style={{ margin: 0, fontFamily: fontsOf(s).display, fontWeight: s.type.displayWeight, fontSize: size, lineHeight: s.type.leading, letterSpacing: s.type.tracking, color: s.colors.ink, overflowWrap: "break-word", ...style }}>
      {words.map((w, i) => {
        const p = interpolate(frame, [at + i * st, at + i * st + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOf(s) });
        const clean = w.replace(/[.,!?]$/, "");
        const tail = w.slice(clean.length);
        const isMark = mark && clean.toLowerCase() === mark.toLowerCase();
        return (
          <span key={i} style={{ display: "inline-block", whiteSpace: "nowrap", opacity: p, transform: `translateY(${(1 - p) * 0.35}em)`, marginRight: "0.22em" }}>
            {isMark ? <Marker at={at + words.length * st + 4}>{clean}</Marker> : clean}
            {tail}
          </span>
        );
      })}
    </h1>
  );
};

/** Ink line art that strokes itself in. Pass SVG path data in the given viewBox. */
export const LineArt: React.FC<{ d: string[]; viewBox: string; width: number; at?: number; stroke?: number; style?: React.CSSProperties }> = ({
  d, viewBox, width, at = 0, stroke = 1.5, style,
}) => {
  const s = useStyle();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.round(s.motion.enter * 2 * (fps / 30));
  return (
    <svg viewBox={viewBox} width={width} style={{ display: "block", overflow: "visible", ...style }} aria-hidden>
      {d.map((path, i) => {
        const len = Math.max(1, getLength(path));
        const start = at + i * staggerOf(s, fps) * 2;
        const p = interpolate(frame, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: drawEaseOf(s) });
        return <path key={i} d={path} fill="none" stroke={s.colors.ink} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${len} ${len}`} strokeDashoffset={len * (1 - p)} />;
      })}
    </svg>
  );
};

/** A row of outlined pills joined by arrows. The pill at `active` fills with ink at `activeAt`. */
export const PillPipeline: React.FC<{ steps: string[]; active?: number; at?: number; activeAt?: number; size?: number }> = ({
  steps, active = -1, at = 0, activeAt, size = 30,
}) => {
  const s = useStyle();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const st = staggerOf(s, fps) * 2;
  const dur = Math.round(s.motion.enter * (fps / 30));
  const fillAt = activeAt ?? at + steps.length * st + dur;
  const fill = interpolate(frame, [fillAt, fillAt + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
      {steps.map((label, i) => {
        const p = interpolate(frame, [at + i * st, at + i * st + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOf(s) });
        const on = i === active ? fill : 0;
        return (
          <React.Fragment key={label}>
            {i > 0 && (
              <svg width={48} height={20} viewBox="0 0 48 20" style={{ opacity: p }} aria-hidden>
                <path d="M2 10 H40 M32 3 L42 10 L32 17" fill="none" stroke={s.colors.ink} strokeWidth={2.5} strokeDasharray="60" strokeDashoffset={60 * (1 - p)} />
              </svg>
            )}
            <span
              style={{
                padding: `${size * 0.4}px ${size * 0.8}px`,
                borderRadius: 999,
                border: `${Math.max(2, s.shape.border * 1.5)}px solid ${s.colors.ink}`,
                background: on > 0 ? s.colors.ink : s.colors.card,
                color: on > 0.5 ? s.colors.bg : s.colors.ink,
                fontFamily: fontsOf(s).display,
                fontWeight: 700,
                fontSize: size,
                opacity: p,
                transform: `translateY(${(1 - p) * 16}px) scale(${1 + 0.08 * Math.sin(on * Math.PI)})`,
              }}
            >
              {label}
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
};

/** The real product in a browser frame. Slides in tilted from the right and settles; may run off the edge. */
export const BrowserFrame: React.FC<{
  src: string; url: string; x: number; y: number; w: number; at?: number; tilt?: boolean; aspect?: number; startFrom?: number;
}> = ({ src, url, x, y, w, at = 0, tilt = true, aspect = 10 / 16, startFrom = 0 }) => {
  const s = useStyle();
  const frame = useCurrentFrame();
  const p = useEnter(at, 2);
  const h = w * aspect;
  const bar = 44;
  const isStill = /\.(png|jpe?g|webp)$/i.test(src);
  const drift = Math.sin((frame - at) / 60) * 0.6;
  const rotY = tilt ? -14 + 6 * p + drift : 0;
  const rotX = tilt ? 7 - 2 * p : 0;
  const ext = /^https?:/.test(src) ? src : staticFile(src);
  return (
    <div
      style={{
        position: "absolute", left: x + (1 - p) * 420, top: y, width: w, height: h + bar,
        background: s.colors.card, border: `${s.shape.border || 1.5}px solid ${s.colors.ink}`, borderRadius: s.shape.radius,
        overflow: "hidden", opacity: Math.min(1, p * 2),
        transform: `perspective(2000px) rotateY(${rotY}deg) rotateX(${rotX}deg)`, transformOrigin: "left center",
        boxShadow: s.shape.shadow === "none" ? undefined : s.shape.shadow,
      }}
    >
      <div style={{ height: bar, display: "flex", alignItems: "center", gap: 8, padding: "0 16px", borderBottom: `1px solid ${s.colors.line}` }}>
        {[0, 1, 2].map((i) => <span key={i} style={{ width: 12, height: 12, borderRadius: 99, border: `1.5px solid ${s.colors.ink}`, opacity: 0.55 }} />)}
        <span style={{ marginLeft: 16, fontFamily: fontsOf(s).mono, fontSize: 18, color: s.colors.muted }}>{url}</span>
      </div>
      {isStill ? (
        <Img src={ext} style={{ width: w, height: h, objectFit: "cover", objectPosition: "left top", display: "block" }} />
      ) : (
        <OffthreadVideo src={ext} startFrom={startFrom} muted style={{ width: w, height: h, objectFit: "cover", display: "block" }} />
      )}
    </div>
  );
};

/** A thick-bordered card that stamps down, slightly rotated. One short line. */
export const StampCard: React.FC<{ text: string; at?: number; rotate?: number; size?: number; style?: React.CSSProperties }> = ({
  text, at = 0, rotate = -2, size = 56, style,
}) => {
  const s = useStyle();
  const p = useEnter(at, 0.6);
  const shadow = s.shape.shadow.startsWith("8px") ? s.shape.shadow : undefined;
  return (
    <div
      style={{
        display: "inline-block", padding: `${size * 0.35}px ${size * 0.55}px`, background: s.colors.card,
        border: `${Math.max(2, s.shape.stampBorder)}px solid ${s.colors.ink}`, borderRadius: Math.min(s.shape.radius, 10),
        fontFamily: fontsOf(s).display, fontWeight: s.type.displayWeight, fontSize: size, letterSpacing: s.type.tracking, color: s.colors.ink,
        opacity: Math.min(1, p * 3), transform: `rotate(${rotate * p}deg) scale(${1.25 - 0.25 * p})`, boxShadow: shadow, ...style,
      }}
    >
      {text}
    </div>
  );
};

/** A big number that counts up, with a mono label. Pass real numbers only. */
export const NumberCard: React.FC<{ value: number; decimals?: number; unit?: string; label: string; note?: string; at?: number; emphasis?: boolean }> = ({
  value, decimals = 0, unit = "", label, note, at = 0, emphasis = false,
}) => {
  const s = useStyle();
  const p = useEnter(at);
  const count = useEnter(at + 4, 2.5);
  const shown = (value * count).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <div style={{ padding: "28px 34px", background: s.colors.card, border: `${s.shape.border || 1.5}px solid ${s.colors.ink}`, borderRadius: s.shape.radius, opacity: p, transform: `translateY(${(1 - p) * 24}px)`, display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
      <span style={{ fontFamily: fontsOf(s).mono, fontSize: 22, color: s.colors.muted }}>{label}</span>
      <span style={{ fontFamily: fontsOf(s).display, fontWeight: s.type.displayWeight, fontSize: 96, lineHeight: 1, letterSpacing: s.type.tracking, color: emphasis ? s.colors.accent : s.colors.ink, fontVariantNumeric: "tabular-nums" }}>
        {shown}
        {unit && <span style={{ fontSize: 44, marginLeft: 8 }}>{unit}</span>}
      </span>
      {note && <span style={{ fontFamily: fontsOf(s).mono, fontSize: 20, color: s.colors.muted }}>{note}</span>}
    </div>
  );
};

/** Ticked list, one row at a time. */
export const Checklist: React.FC<{ items: string[]; at?: number; size?: number }> = ({ items, at = 0, size = 36 }) => {
  const s = useStyle();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const st = staggerOf(s, fps) * 3;
  const dur = Math.round(s.motion.enter * (fps / 30));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: size * 0.5 }}>
      {items.map((it, i) => {
        const p = interpolate(frame, [at + i * st, at + i * st + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easeOf(s) });
        return (
          <div key={it} style={{ display: "flex", alignItems: "center", gap: size * 0.45, fontSize: size, fontWeight: 600, opacity: p, transform: `translateX(${(1 - p) * -20}px)` }}>
            <span style={{ width: size * 1.05, height: size * 1.05, flex: "none", background: s.colors.ink, color: s.colors.bg, display: "flex", alignItems: "center", justifyContent: "center", fontSize: size * 0.7, borderRadius: Math.min(4, s.shape.radius), transform: `scale(${0.6 + 0.4 * p})` }}>✓</span>
            <span>{it}</span>
          </div>
        );
      })}
    </div>
  );
};

/** The voiceover line at the bottom of the frame, for silent autoplay. */
export const CaptionBar: React.FC<{ text: string; at?: number }> = ({ text, at = 0 }) => {
  const s = useStyle();
  const p = useEnter(at);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 96, padding: "0 112px", display: "flex", alignItems: "center", borderTop: `1px solid ${s.colors.line}`, background: s.colors.bg, fontSize: 30, color: s.colors.muted, opacity: p }}>
      {text}
    </div>
  );
};

/** Close: mark, wordmark, one action, the address, small credits. */
export const CloseCard: React.FC<{ mark?: React.ReactNode; name: string; cta: string; url: string; credits?: string[]; at?: number }> = ({
  mark, name, cta, url, credits = [], at = 0,
}) => {
  const s = useStyle();
  const a = useEnter(at);
  const b = useEnter(at + 10);
  const c = useEnter(at + 20);
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 220px", gap: 44 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 32, opacity: a, transform: `translateY(${(1 - a) * 20}px)` }}>
        {mark}
        <span style={{ fontFamily: fontsOf(s).display, fontWeight: s.type.displayWeight, fontSize: 120, letterSpacing: s.type.tracking, lineHeight: 1 }}>{name}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 36, opacity: b, transform: `translateY(${(1 - b) * 20}px)` }}>
        <span style={{ padding: "20px 36px", background: s.colors.marker, color: s.colors.onMarker, fontWeight: 800, fontSize: 38, borderRadius: Math.min(s.shape.radius, 10) }}>{cta}</span>
        <span style={{ fontFamily: fontsOf(s).mono, fontSize: 32 }}>{url}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, opacity: c, fontFamily: fontsOf(s).mono, fontSize: 22, color: s.colors.muted }}>
        {credits.map((t) => <span key={t}>{t}</span>)}
      </div>
    </AbsoluteFill>
  );
};
