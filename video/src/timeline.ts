// Timing comes from the voice: one continuous take (tools/voice.py -> src/voice.json, word timings in seconds).
// Each scene starts a beat before its first word; scenes overlap by OVER frames for the push transition.
import voice from "./voice.json";
import script from "../script.json";

export const FPS = 30;
export const LEAD = 15; // frames of quiet before the first word
export const PRE = 6; // a scene arrives this many frames before its first word
export const OVER = 12; // push transition length
const TAIL = 66; // hold on the close after the last word

type Scene = { scene: string; start: number; end: number; words: [number, number, string][] };
const V = voice as Scene[];
const toFrame = (sec: number) => Math.round(sec * FPS) + LEAD;

export const STARTS = V.map((s, i) => (i === 0 ? 0 : toFrame(s.start) - PRE));
export const ENDS = V.map((s, i) => (i < V.length - 1 ? STARTS[i + 1] : toFrame(s.end) + TAIL));
export const TOTAL = ENDS[ENDS.length - 1];

const norm = (w: string) => w.toLowerCase().replace(/’/g, "'").replace(/[^a-z0-9']/g, "");

/** Absolute frame where `text` (first word that starts with it, nth match) is spoken in scene `id`. */
export const wordAt = (id: string, text: string, nth = 0): number => {
  const s = V.find((x) => x.scene === id)!;
  const hits = s.words.filter((w) => norm(w[2]).startsWith(norm(text)));
  const w = hits[nth] ?? hits[hits.length - 1];
  if (!w) throw new Error(`"${text}" not spoken in ${id}`);
  return toFrame(w[0]);
};

/** Frame relative to the scene's own start (what useCurrentFrame() returns inside it). */
export const rel = (id: string, text: string, nth = 0) => wordAt(id, text, nth) - sceneFrom(V.findIndex((x) => x.scene === id));

/** Where scene i's Sequence begins: OVER frames before its start, so the push lands on the first word. */
export const sceneFrom = (i: number) => (i === 0 ? 0 : STARTS[i] - OVER);

/** Caption cues for the whole film: each sentence from the frame its first word is spoken. */
export const CAPTIONS: [number, string][] = (() => {
  const cues: [number, string][] = [];
  for (const s of script) {
    const sc = V.find((x) => x.scene === s.id)!;
    let i = 0;
    // keep "p.m." and "a.m." from ending a sentence
    const safe = s.text.replace(/([ap])\.m\./g, "$1~m~");
    for (const raw of safe.match(/[^.?!]+[.?!]+/g) ?? [safe]) {
      const sentence = raw.replace(/([ap])~m~/g, "$1.m.");
      const first = norm(sentence.trim().split(" ")[0]);
      while (i < sc.words.length && first !== norm(sc.words[i][2].split(" ")[0])) i++;
      cues.push([toFrame(sc.words[Math.min(i, sc.words.length - 1)][0]), sentence.trim()]);
      i++;
    }
  }
  return cues;
})();
