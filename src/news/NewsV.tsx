import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Audio, Img, Sequence, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

// Vertical (1080×1920) German literature short in the style of the owner's sample (14/11/2026, a Vietnamese
// video on Lev Tolstoy): one picture at a time filling the whole frame (portraits of the writer, paintings,
// photographs) with a slow, steady push-in, hard cuts between pictures, and subtitles timed to the voice as dark
// text on yellow boxes (one box per row) a little below the middle. No titles, no cards, no on-screen credits
// (they go in the video description). The plan (props) is written by scripts/news/build.py; see AGENT_NEWS.md.
type Cam = { z: number; x: number; y: number };
// move: the name of the catalogue move ("bảng cách edit", scripts/news/moves.py) the camera numbers came from
// (information only; build.py already worked out from/to). fade: seconds this picture takes to dissolve in over the
// one before; leave it out for a hard cut, as in the sample.
export type Pic = { src: string; w: number; h: number; s: number; e: number; from: Cam; to: Cam; move?: string; fade?: number };
export type ChapterV = { s: number; e: number; pics: Pic[] };
export type SubV = { s: number; e: number; text: string };
type FontChunk = { family: string; file: string; range: string };
// The shared hook of a "Top X" series (owner 18/11/2026, build.py from picks.json "top"): until gridEnd (line 1) the
// title and every person of the list as a round portrait with the name; until badgeEnd (line 2) a big "PLATZ <rank>".
export type TopPerson = { src: string; w: number; h: number; name: string; fx: number; fy: number; zoom: number; me: boolean };
export type TopV = { title: string[]; label: string; people: TopPerson[]; gridEnd: number; badgeEnd: number };
export type PlanV = { duration: number; chapters: ChapterV[]; subs: SubV[]; voice: { s: number; src: string }[]; music: string | null; musicVolume: number;
  fonts: FontChunk[]; top?: TopV };

const W = 1080, H = 1920;
const SUB_Y = 1496;                       // vertical centre of the subtitle block (78 % of the height, as in the sample)
const YELLOW = '#eec514', INK = '#1e1006';
const FONT = 'Philosopher, sans-serif';
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const popIn = (k: number) => { const q = clamp01(k) - 1; return 1 + 2.2 * q * q * q + 1.2 * q * q; };   // 0 → 1 with a small overshoot

let fontsLoading: Promise<void> | null = null;
const useFonts = (fonts: FontChunk[], text: string) => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    (fontsLoading ??= (async () => {
      for (const f of fonts)
        document.fonts.add(new FontFace(f.family, `url(${staticFile(f.file)}) format('woff2')`, { weight: '400', unicodeRange: f.range }));
      await document.fonts.load(`400 50px ${FONT}`, text);
    })()).then(() => continueRender(h)).catch((e) => cancelRender(e));
  }, [h, fonts, text]);
};

// one picture filling the frame, moving steadily from `from` to `to` (cover-fit, clamped so no edge shows)
const PicView: React.FC<{ p: Pic; t: number }> = ({ p, t }) => {
  const k = clamp01((t - p.s) / Math.max(0.5, p.e - p.s));
  const z = p.from.z + (p.to.z - p.from.z) * k, x = p.from.x + (p.to.x - p.from.x) * k, y = p.from.y + (p.to.y - p.from.y) * k;
  const c = Math.max(W / p.w, H / p.h) * z, dw = p.w * c, dh = p.h * c;
  const left = Math.min(0, Math.max(W - dw, W / 2 - x * dw)), top = Math.min(0, Math.max(H - dh, H / 2 - y * dh));
  return <Img src={staticFile(p.src)} style={{ position: 'absolute', left, top, width: dw, height: dh, maxWidth: 'none' }} />;
};

// subtitle rows as yellow boxes that touch each other, each as wide as its own row
const Subtitle: React.FC<{ text: string }> = ({ text }) => {
  const rows = text.split('\n');
  const size = Math.min(50, Math.floor(940 / (Math.max(...rows.map((r) => r.length)) * 0.47)));
  return (
    <div style={{ position: 'absolute', left: 40, right: 40, top: SUB_Y, transform: 'translateY(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {rows.map((r, i) => (
        <div key={i} style={{ fontFamily: FONT, fontWeight: 400, fontSize: size, lineHeight: 1.22, color: INK, background: YELLOW, padding: '4px 14px 6px',
          borderRadius: 10, whiteSpace: 'nowrap', marginTop: i ? -6 : 0 }}>{r}</div>
      ))}
    </div>
  );
};

// yellow boxes like the subtitles, bigger: the title of the grid and the "PLATZ 5" badge
const Boxes: React.FC<{ rows: string[]; size: number; y: number; scale?: number; opacity?: number }> = ({ rows, size, y, scale = 1, opacity = 1 }) => (
  <div style={{ position: 'absolute', left: 30, right: 30, top: y, transform: `translateY(-50%) scale(${scale})`, opacity, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
    {rows.map((r, i) => (
      <div key={i} style={{ fontFamily: FONT, fontWeight: 400, fontSize: size, lineHeight: 1.18, color: INK, background: YELLOW, padding: '6px 22px 10px',
        borderRadius: 14, whiteSpace: 'nowrap', marginTop: i ? -8 : 0 }}>{r}</div>
    ))}
  </div>
);

// one round portrait: the picture covers the circle × zoom with its focus point at the centre (moves.circle_window)
const Round: React.FC<{ p: TopPerson; d: number }> = ({ p, d }) => {
  const c = (d / Math.min(p.w, p.h)) * Math.max(1, p.zoom), dw = p.w * c, dh = p.h * c;
  const left = Math.min(0, Math.max(d - dw, d / 2 - p.fx * dw)), top = Math.min(0, Math.max(d - dh, d / 2 - p.fy * dh));
  return <Img src={staticFile(p.src)} style={{ position: 'absolute', left, top, width: dw, height: dh, maxWidth: 'none' }} />;
};

// line 1 of a Top X video: the title and the round portraits of the whole list (rows of three; four as two and two)
const TopGrid: React.FC<{ top: TopV; t: number }> = ({ top, t }) => {
  const n = top.people.length, per = n === 4 ? 2 : 3, rows: TopPerson[][] = [];
  for (let k = 0; k < n; k += per) rows.push(top.people.slice(k, k + per));
  const gap = 70, m = Math.min(per, n), d = Math.min(340, Math.floor((1000 - (m - 1) * gap) / m)), rowH = d + 120;   // the widest row fits the frame
  const y0 = 1020 - ((rows.length - 1) * rowH) / 2;
  const mark = clamp01((t - (top.gridEnd - 0.9)) / 0.4);          // the last moment: this video's writer lights up
  let k = -1;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: 'rgba(14,10,6,0.8)' }} />
      <Boxes rows={top.title} size={top.title.some((r) => r.length > 22) ? 64 : 76} y={330} opacity={clamp01(t / 0.25)} />
      {rows.map((row, ri) => row.map((p, j) => {
        k += 1;
        const cx = 540 + (j - (row.length - 1) / 2) * (d + gap), cy = y0 + ri * rowH;
        const sc = popIn((t - 0.2 - k * 0.12) / 0.35) * (p.me ? 1 + 0.12 * mark : 1);
        const dim = p.me ? 1 : 1 - 0.55 * mark;
        const size = Math.min(44, Math.floor((d + gap - 10) / (p.name.length * 0.5)));
        return (
          <div key={p.src + k} style={{ position: 'absolute', left: cx - d / 2, top: cy - d / 2, width: d, transform: `scale(${sc})`, opacity: dim }}>
            <div style={{ position: 'relative', width: d, height: d, borderRadius: '50%', overflow: 'hidden',
              boxShadow: `0 0 0 ${p.me && mark > 0 ? 10 : 5}px ${p.me && mark > 0 ? YELLOW : '#f4ecd8'}, 0 12px 30px rgba(0,0,0,0.6)` }}>
              <Round p={p} d={d} />
            </div>
            <div style={{ position: 'absolute', left: -gap / 2, right: -gap / 2, top: d + 22, textAlign: 'center', fontFamily: FONT, fontSize: size,
              color: '#fff', textShadow: '0 2px 6px rgba(0,0,0,0.9)', whiteSpace: 'nowrap' }}>{p.name}</div>
          </div>
        );
      }))}
    </AbsoluteFill>
  );
};

export const NewsV: React.FC<PlanV> = (plan) => {
  useFonts(plan.fonts, plan.subs.map((s) => s.text).join('') + (plan.top ? plan.top.title.join('') + plan.top.label + plan.top.people.map((p) => p.name).join('') : ''));
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  const pics = plan.chapters.flatMap((c) => c.pics);
  if (!pics.length) return <AbsoluteFill style={{ backgroundColor: '#000' }} />;
  const k = pics.findIndex((p) => t >= p.s && t < p.e);
  const i = k >= 0 ? k : t >= pics[pics.length - 1].s ? pics.length - 1 : 0;
  const pic = pics[i];                                                          // hard cuts, unless the shot asks for a dissolve
  const fade = Math.min(pic.fade ?? 0, 1.5), inA = fade > 0 && i > 0 ? clamp01((t - pic.s) / fade) : 1;
  const sub = plan.subs.find((s) => t >= s.s && t < s.e);
  const endFade = clamp01((t - (plan.duration - 1.2)) / 1.2);
  const speaking = (tt: number) => plan.subs.some((s) => tt >= s.s - 0.2 && tt < s.e + 0.3);
  return (
    <AbsoluteFill style={{ backgroundColor: '#000', overflow: 'hidden' }}>
      {inA < 1 ? <PicView p={pics[i - 1]} t={t} /> : null}
      <AbsoluteFill style={{ opacity: inA }}><PicView p={pic} t={t} /></AbsoluteFill>
      {plan.top && t < plan.top.gridEnd ? <TopGrid top={plan.top} t={t} /> : null}
      {plan.top && t >= plan.top.gridEnd && t < plan.top.badgeEnd
        ? <Boxes rows={[plan.top.label]} size={130} y={300} scale={popIn((t - plan.top.gridEnd) / 0.3)} /> : null}
      {sub && !(plan.top && t < plan.top.gridEnd) ? <Subtitle text={sub.text} /> : null}
      <AbsoluteFill style={{ backgroundColor: '#000', opacity: endFade }} />
      {plan.voice.map((v, i) => <Sequence key={i} from={Math.round(v.s * fps)}><Audio src={staticFile(v.src)} /></Sequence>)}
      {plan.music ? (
        <Audio src={staticFile(plan.music)} volume={(f) => {
          const tt = f / fps;
          return plan.musicVolume * Math.max(0, Math.min(1, tt / 0.8, (durationInFrames / fps - tt) / 1.5)) * (speaking(tt) ? 0.7 : 1);
        }} />
      ) : null}
    </AbsoluteFill>
  );
};
