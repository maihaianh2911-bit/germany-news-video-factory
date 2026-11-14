import React from 'react';
import { Composition } from 'remotion';
import { NewsV, PlanV } from './NewsV';

const FPS = 30;
// The whole plan comes in as props (scripts/news/build.py), its length included.
const EMPTY: PlanV = { duration: 1, chapters: [], subs: [], voice: [], music: null, musicVolume: 0.3, fonts: [] };

export const NewsRoot: React.FC = () => (
  <Composition
    id="NewsV"
    component={NewsV as unknown as React.FC<Record<string, unknown>>}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={FPS}
    defaultProps={EMPTY as unknown as Record<string, unknown>}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.ceil((props as unknown as PlanV).duration * FPS)) })}
  />
);
