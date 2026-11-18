// Editorial Paper from the style library, skinned with the planner's own tokens (src/ps1/web/planner.css).
import { loadFont as loadManrope } from "@remotion/google-fonts/Manrope";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { getStyle } from "./kit/styles";

loadManrope("normal", { weights: ["500", "600", "700", "800"], subsets: ["latin"] });
loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] });

const base = getStyle("editorial-paper", {
  colors: {
    bg: "#F8F9FA", card: "#FFFFFF", ink: "#202124", muted: "#5F6368", line: "#DADCE0",
    accent: "#1A73E8", marker: "#AECBFA", onMarker: "#202124", onAccent: "#FFFFFF",
  },
  fonts: { display: "Manrope", body: "Manrope", mono: "JetBrains Mono" },
});

export const STYLE = { ...base, type: { ...base.type, tracking: "-0.03em", leading: 1.02 } };
export const C = { ...STYLE.colors, timetable: "#9AA0A6", drop: "#D93025", track: "#E8EAED" };
export const SANS = '"Manrope", system-ui, sans-serif';
export const MONO = '"JetBrains Mono", ui-monospace, monospace';
export const FPS = 30;
