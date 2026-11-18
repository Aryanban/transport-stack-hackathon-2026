import React from "react";
import { Composition } from "remotion";
import { Film, TOTAL } from "./Film";
import { FPS } from "./theme";

export const Root: React.FC = () => (
  <Composition id="Film" component={Film} durationInFrames={TOTAL} fps={FPS} width={1920} height={1080} />
);
