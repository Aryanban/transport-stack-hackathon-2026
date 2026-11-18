// The film: one continuous voice take; each scene arrives on its first word and pushes the last one out.
import React from "react";
import { AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { StyleProvider } from "./kit/Editorial";
import { S1, S2, S3, S4, S5, S6, S7, S8 } from "./Scenes";
import { C, SANS, STYLE } from "./theme";
import { CAPTIONS, ENDS, LEAD, OVER, TOTAL, sceneFrom } from "./timeline";

export { TOTAL };
const SCENES = [S1, S2, S3, S4, S5, S6, S7, S8];
const push = Easing.bezier(0.65, 0, 0.35, 1);

/** Slides in from the right over OVER frames; the scene underneath drifts left and dims. */
const Push: React.FC<{ first: boolean; dur: number; children: React.ReactNode }> = ({ first, dur, children }) => {
  const f = useCurrentFrame();
  const opts = { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: push } as const;
  const enter = first ? 1 : interpolate(f, [0, OVER], [0, 1], opts);
  const leave = interpolate(f, [dur - OVER, dur], [0, 1], opts);
  return (
    <AbsoluteFill style={{ background: C.bg, transform: `translateX(${(1 - enter) * 100 - leave * 30}%)`, boxShadow: enter < 1 ? "-30px 0 60px rgb(32 33 36 / 0.12)" : undefined }}>
      {children}
    </AbsoluteFill>
  );
};

const Captions: React.FC = () => {
  const f = useCurrentFrame();
  let text = "";
  for (const [at, line] of CAPTIONS) if (f >= at) text = line;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 96, padding: "0 112px", display: "flex", alignItems: "center", borderTop: `1px solid ${C.line}`, background: C.bg, fontFamily: SANS, fontSize: 30, fontWeight: 500, color: C.muted }}>
      {text}
    </div>
  );
};

export const Film: React.FC = () => (
  <StyleProvider style={STYLE}>
    <AbsoluteFill style={{ background: C.bg, color: C.ink, fontFamily: SANS }}>
      {SCENES.map((Scene, i) => {
        // each scene starts OVER frames early (except the first) so the push lands on its first word
        const from = sceneFrom(i);
        const dur = ENDS[i] - from;
        return (
          <Sequence key={i} from={from} durationInFrames={dur} name={`S${i + 1}`}>
            <Push first={i === 0} dur={i === SCENES.length - 1 ? dur + 9999 : dur}>
              <Scene />
            </Push>
          </Sequence>
        );
      })}
      <Captions />
      <Sequence from={LEAD} layout="none">
        <Audio src={staticFile("vo/full.mp3")} />
      </Sequence>
    </AbsoluteFill>
  </StyleProvider>
);
