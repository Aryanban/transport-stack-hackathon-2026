// The style library in code. Data lives in styles.json (shared with tools/style/pick-style.mjs
// and the remotion-video-director skill). Pick a style with `npm run style:pick -- "<brief>"`,
// then pass its id to getStyle(). A brand skin swaps colours and fonts, never structure or motion.

import { Easing } from "remotion";
import { loadFont as archivo } from "@remotion/google-fonts/Archivo";
import { loadFont as bricolage } from "@remotion/google-fonts/BricolageGrotesque";
import { loadFont as dmMono } from "@remotion/google-fonts/DMMono";
import { loadFont as familjen } from "@remotion/google-fonts/FamiljenGrotesk";
import { loadFont as geistMono } from "@remotion/google-fonts/GeistMono";
import { loadFont as hanken } from "@remotion/google-fonts/HankenGrotesk";
import { loadFont as plexMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as plexSans } from "@remotion/google-fonts/IBMPlexSans";
import { loadFont as instrument } from "@remotion/google-fonts/InstrumentSans";
import { loadFont as jetbrains } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as newsreader } from "@remotion/google-fonts/Newsreader";
import { loadFont as jakarta } from "@remotion/google-fonts/PlusJakartaSans";
import { loadFont as spaceMono } from "@remotion/google-fonts/SpaceMono";
import { loadFont as syne } from "@remotion/google-fonts/Syne";
import data from "./styles.json";

export type StyleColors = {
  bg: string; card: string; ink: string; muted: string; line: string;
  accent: string; marker: string; onMarker: string; onAccent: string; up?: string; down?: string;
};

export type StyleSpec = {
  id: string;
  name: string;
  feel: string;
  reference: string;
  bestFor: string[];
  signals: string[];
  avoid: string[];
  colors: StyleColors;
  fonts: { display: string; body: string; mono: string };
  type: { displayWeight: number; tracking: string; leading: number; case: string };
  shape: { radius: number; border: number; stampBorder: number; shadow: string };
  motion: { ease: number[]; draw: number[]; enter: number; stagger: number; camera: string; cuts: string };
  texture: string;
  components: string[];
  rules: string[];
};

/** A brand's own tokens laid over a style: colours and fonts only. */
export type BrandSkin = { colors?: Partial<StyleColors>; fonts?: Partial<StyleSpec["fonts"]> };

export const STYLES = data.styles as StyleSpec[];
export type StyleId = (typeof STYLES)[number]["id"];

const LOADERS: Record<string, (style: "normal", opts: { weights: string[]; subsets: string[] }) => { fontFamily: string }> = {
  Archivo: archivo as never,
  "Bricolage Grotesque": bricolage as never,
  "DM Mono": dmMono as never,
  "Familjen Grotesk": familjen as never,
  "Geist Mono": geistMono as never,
  "Hanken Grotesk": hanken as never,
  "IBM Plex Mono": plexMono as never,
  "IBM Plex Sans": plexSans as never,
  "Instrument Sans": instrument as never,
  "JetBrains Mono": jetbrains as never,
  Newsreader: newsreader as never,
  "Plus Jakarta Sans": jakarta as never,
  "Space Mono": spaceMono as never,
  Syne: syne as never,
};

const loaded = new Set<string>();
const loadFamily = (name: string, weights: string[]) => {
  const key = `${name}:${weights.join(",")}`;
  if (loaded.has(key)) return;
  loaded.add(key);
  const loader = LOADERS[name];
  // A skin font not in the table must be loaded by the project itself (e.g. a local @font-face).
  if (!loader) return;
  // Families ship different weights (Space Mono has only 400 and 700): load each one that exists.
  for (const w of weights) {
    try {
      loader("normal", { weights: [w], subsets: ["latin"] });
    } catch {
      // weight not offered by this family; the browser falls back to the nearest one
    }
  }
};

export const getStyle = (id: string, skin: BrandSkin = {}): StyleSpec => {
  const base = STYLES.find((s) => s.id === id);
  if (!base) throw new Error(`Unknown style "${id}". Known: ${STYLES.map((s) => s.id).join(", ")}`);
  return { ...base, colors: { ...base.colors, ...skin.colors }, fonts: { ...base.fonts, ...skin.fonts } };
};

/** Load the style's fonts once, at module level of the scene or Root. */
export const loadStyleFonts = (s: StyleSpec) => {
  const w = String(s.type.displayWeight);
  loadFamily(s.fonts.display, Array.from(new Set(["500", "600", w])));
  loadFamily(s.fonts.body, ["400", "500", "600"]);
  loadFamily(s.fonts.mono, ["400", "500"]);
};

export const easeOf = (s: StyleSpec) => Easing.bezier(...(s.motion.ease as [number, number, number, number]));
export const drawEaseOf = (s: StyleSpec) => Easing.bezier(...(s.motion.draw as [number, number, number, number]));

/** Font stacks ready for CSS. */
export const fontsOf = (s: StyleSpec) => ({
  display: `"${s.fonts.display}", system-ui, sans-serif`,
  body: `"${s.fonts.body}", system-ui, sans-serif`,
  mono: `"${s.fonts.mono}", ui-monospace, monospace`,
});
