import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Audio, Img, Sequence, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

// Vertical (1080×1920) German news short: real, free-to-use pictures in a panel on top (slow camera moves,
// cross-fades), with optional chapter cards and timed subtitles below on a dark ink background.
// The plan (props) is written by scripts/news/build.py; see AGENT_NEWS.md.
type Cam = { z: number; x: number; y: number };
type Print = { src: string; w: number; h: number };
export type Pic = { src: string; w: number; h: number; s: number; e: number; from: Cam; to: Cam; tag?: string; credit?: string;
  pair?: { left: Print & { caption: string[] }; right: Print } }; // pair: two framed prints instead of a full-panel picture
export type Pair = { s: number; e: number; left: { src: string; w: number; h: number; caption: string[] }; right: { src: string; w: number; h: number }; credit?: string };
export type ChapterV = { s: number; e: number; num: string; label: string; title: string; desc: string[]; pics: Pic[] };
export type SubV = { s: number; e: number; text: string; hl: string[] };
type FontChunk = { family: string; file: string; range: string };
export type PlanV = { duration: number; chapters: ChapterV[]; subs: SubV[]; voice: { s: number; src: string }[]; music: string | null; musicVolume: number;
  fonts: FontChunk[]; grain: string[]; showChapters?: boolean };

const W = 1080, H = 1920, PH = 1000; // picture panel height (the bottom ~300 px stay free for the platform's buttons and caption)
const GOLD = '#d9b56a', INK = '#0a0f1a', CREAM = '#f3ece0', GREY = '#9aa3b2';
const SERIF = '"Source Serif 4", serif', SANS = '"Source Sans 3", sans-serif';
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const ease = (x: number) => { const p = clamp01(x); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);

let fontsLoading: Promise<void> | null = null;
const useFonts = (fonts: FontChunk[], text: string) => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    (fontsLoading ??= (async () => {
      for (const f of fonts)
        document.fonts.add(new FontFace(f.family, `url(${staticFile(f.file)}) format('woff2')`, { weight: '100 900', unicodeRange: f.range }));
      await Promise.all([700, 500, 400].flatMap((wt) => [document.fonts.load(`${wt} 60px ${SERIF}`, text), document.fonts.load(`${wt} 40px ${SANS}`, text)]));
    })()).then(() => continueRender(h)).catch((e) => cancelRender(e));
  }, [h, fonts, text]);
};

// one picture filling the panel, moving from `from` to `to` (cover-fit, clamped so no edge shows)
const PicView: React.FC<{ p: Pic; t: number }> = ({ p, t }) => {
  if (p.pair) return <PairView p={{ s: p.s, e: p.e, left: p.pair.left, right: p.pair.right }} t={t} />;
  const k = ease((t - p.s) / Math.max(0.5, p.e - p.s));
  const z = p.from.z + (p.to.z - p.from.z) * k, x = p.from.x + (p.to.x - p.from.x) * k, y = p.from.y + (p.to.y - p.from.y) * k;
  const c = Math.max(W / p.w, PH / p.h) * z, dw = p.w * c, dh = p.h * c;
  const left = Math.min(0, Math.max(W - dw, W / 2 - x * dw)), top = Math.min(0, Math.max(PH - dh, PH / 2 - y * dh));
  return <Img src={staticFile(p.src)} style={{ position: 'absolute', left, top, width: dw, height: dh, maxWidth: 'none' }} />;
};

// portrait photo + book cover as framed prints on a dark background
const PairView: React.FC<{ p: Pair; t: number }> = ({ p, t }) => {
  const k = ease((t - p.s) / Math.max(0.5, p.e - p.s));
  const z = 1 + 0.05 * k;
  const top = Math.min(150, PH - 330 - (400 * p.left.h) / p.left.w); // tall portraits move up so the caption clears the credit line
  const frame = (src: string, w: number, h: number, bw: number, x: number, y: number, rot: number, d: number) => {
    const bh = (bw * h) / w;
    const a = easeOut((t - p.s - d) / 0.9);
    return (
      <div style={{ position: 'absolute', left: x, top: y + (1 - a) * 30, width: bw + 24, opacity: a, transform: `rotate(${rot}deg)`,
        background: '#efe7d6', padding: 12, boxShadow: '0 30px 60px rgba(0,0,0,.55), 0 4px 10px rgba(0,0,0,.4)' }}>
        <Img src={staticFile(src)} style={{ display: 'block', width: bw, height: bh }} />
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ transform: `scale(${z})`, transformOrigin: '50% 45%' }}>
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 40%, #2a2318 0%, #15120d 55%, #0a0f1a 100%)' }} />
      {frame(p.left.src, p.left.w, p.left.h, 400, 70, top, -2.2, 0)}
      {frame(p.right.src, p.right.w, p.right.h, 440, 560, top - 40, 1.8, 0.35)}
      <div style={{ position: 'absolute', left: 70, top: top + (400 * p.left.h) / p.left.w + 60, width: 424, textAlign: 'center', opacity: easeOut((t - p.s - 0.7) / 0.8) }}>
        <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: Math.min(46, Math.floor(424 / (p.left.caption[0].length * 0.58))), color: CREAM, letterSpacing: '0.02em' }}>{p.left.caption[0]}</div>
        <div style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 24, color: GREY, letterSpacing: '0.03em', marginTop: 6 }}>{p.left.caption[1]}</div>
      </div>
    </AbsoluteFill>
  );
};

const Highlight: React.FC<{ text: string; hl: string[] }> = ({ text, hl }) => {
  if (!hl.length) return <>{text}</>;
  const re = new RegExp(`(${hl.map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g');
  return <>{text.split(re).map((part, i) => (hl.includes(part) ? <span key={i} style={{ color: GOLD }}>{part}</span> : <span key={i}>{part}</span>))}</>;
};

export const NewsV: React.FC<PlanV> = (plan) => {
  useFonts(plan.fonts, plan.chapters.map((c) => c.num + c.label + c.title + c.desc.join('') + c.pics.map((p) => (p.tag || '') + (p.credit || '') + (p.pair ? p.pair.left.caption.join('') : '')).join('')).join('') + plan.subs.map((s) => s.text).join(''));
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  const showChapters = plan.showChapters !== false;
  if (!plan.chapters.length) return <AbsoluteFill style={{ backgroundColor: INK }} />;
  const ci = Math.max(0, plan.chapters.findIndex((c) => t >= c.s && t < c.e));
  const ch = plan.chapters[ci] || plan.chapters[plan.chapters.length - 1];
  const prev = ci > 0 ? plan.chapters[ci - 1] : null;
  const X = 0.7; // cross-fade between chapters (pictures) and text slide
  const inA = ci === 0 ? 1 : easeOut((t - ch.s) / X);
  // pictures: current chapter (+ the previous one underneath while it fades)
  const picsOf = (c: ChapterV) => c.pics;
  const visible = (c: ChapterV) => picsOf(c).filter((p) => t >= p.s - X && t < p.e + X);
  const picLayer = (c: ChapterV, key: string) => (
    <AbsoluteFill key={key}>
      {visible(c).map((p, i) => <AbsoluteFill key={i} style={{ opacity: clamp01((t - (p.s - X)) / X) }}><PicView p={p} t={t} /></AbsoluteFill>)}
    </AbsoluteFill>
  );
  const curPic = picsOf(ch).find((p) => t >= p.s && t < p.e) || picsOf(ch)[picsOf(ch).length - 1];
  const tag = curPic?.tag, credit = curPic?.credit;
  const sub = plan.subs.find((s) => t >= s.s - 0.1 && t < s.e + 0.25);
  const subA = sub ? Math.min(clamp01((t - (sub.s - 0.1)) / 0.25), clamp01((sub.e + 0.25 - t) / 0.25)) : 0;
  const endFade = clamp01((t - (plan.duration - 1.6)) / 1.6);
  const startFade = 1 - clamp01(t / 0.8);
  const speaking = (tt: number) => plan.subs.some((s) => tt >= s.s - 0.2 && tt < s.e + 0.3);
  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      {/* picture panel */}
      <div style={{ position: 'absolute', left: 0, top: 0, width: W, height: PH, overflow: 'hidden' }}>
        {prev && t < ch.s + X ? picLayer(prev, 'p') : null}
        <AbsoluteFill style={{ opacity: inA }}>{picLayer(ch, 'c')}</AbsoluteFill>
        <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(10,15,26,.35) 0%, rgba(10,15,26,0) 14%, rgba(10,15,26,0) 70%, ${INK} 100%)` }} />
        {tag ? (
          <div style={{ position: 'absolute', right: 48, top: 64, padding: '10px 20px', background: 'rgba(10,15,26,.62)', border: `1px solid rgba(217,181,106,.55)`,
            fontFamily: SERIF, fontWeight: 500, fontSize: 28, color: CREAM, letterSpacing: '0.06em', opacity: inA }}>{tag}</div>
        ) : null}
        {credit ? (
          <div style={{ position: 'absolute', left: 48, bottom: 40, right: 48, fontFamily: SANS, fontWeight: 400, fontSize: 20, color: 'rgba(230,224,212,.62)', letterSpacing: '0.01em', opacity: inA }}>{credit}</div>
        ) : null}
      </div>
      {showChapters ? (
        <>
          {/* chapter progress */}
          <div style={{ position: 'absolute', left: 72, right: 72, top: 1028, display: 'flex', gap: 10 }}>
            {plan.chapters.map((c, i) => {
              const fill = i < ci ? 1 : i > ci ? 0 : clamp01((t - c.s) / (c.e - c.s));
              return <div key={i} style={{ flex: 1, height: 3, background: 'rgba(255,255,255,.14)' }}><div style={{ width: `${fill * 100}%`, height: 3, background: GOLD }} /></div>;
            })}
          </div>
          {/* chapter card */}
          {(() => {
            const a = easeOut((t - ch.s - 0.15) / 0.8);
            return (
              <div style={{ position: 'absolute', left: 72, right: 72, top: 1072 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, opacity: a, transform: `translateY(${(1 - a) * 16}px)` }}>
                  <span style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 30, color: GOLD, letterSpacing: '0.08em' }}>{ch.num}</span>
                  <span style={{ width: 56 * a, height: 1.5, background: GOLD }} />
                  <span style={{ fontFamily: SANS, fontWeight: 500, fontSize: 28, color: GOLD, letterSpacing: '0.18em', textTransform: 'uppercase' }}>{ch.label}</span>
                </div>
                <div style={{ marginTop: 26, fontFamily: SERIF, fontWeight: 700, fontSize: Math.min(76, Math.floor(936 / (Math.max(8, ch.title.length) * 0.56))), lineHeight: 1.25, color: CREAM, letterSpacing: '0.005em', whiteSpace: 'nowrap',
                  opacity: easeOut((t - ch.s - 0.3) / 0.8), transform: `translateY(${(1 - easeOut((t - ch.s - 0.3) / 0.8)) * 22}px)`, filter: `blur(${(1 - easeOut((t - ch.s - 0.3) / 0.8)) * 6}px)` }}>{ch.title}</div>
                <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 4, opacity: easeOut((t - ch.s - 0.75) / 0.8) }}>
                  {ch.desc.map((d, i) => <div key={i} style={{ fontFamily: SANS, fontWeight: 400, fontSize: 32, lineHeight: 1.5, color: GREY, letterSpacing: '0.01em' }}>{d}</div>)}
                </div>
              </div>
            );
          })()}
        </>
      ) : null}
      {/* subtitle */}
      {sub ? (
        <div style={{ position: 'absolute', left: 60, right: 60, top: showChapters ? 1418 : 1190, textAlign: 'center', opacity: subA, transform: `translateY(${(1 - subA) * 10}px)` }}>
          {showChapters ? <div style={{ display: 'inline-block', width: 64, height: 2, background: 'rgba(217,181,106,.6)', marginBottom: 26 }} /> : null}
          {sub.text.split('\n').map((l, i, all) => (
            <div key={i} style={{ fontFamily: SANS, fontWeight: 700, fontSize: Math.min(58, Math.floor(950 / (Math.max(...all.map((x) => x.length)) * 0.58))), lineHeight: 1.4, color: '#ffffff', letterSpacing: '0.01em', whiteSpace: 'nowrap', textShadow: '0 2px 18px rgba(0,0,0,.6)' }}>
              <Highlight text={l} hl={sub.hl} />
            </div>
          ))}
        </div>
      ) : null}
      {plan.grain.length ? <Img src={staticFile(plan.grain[Math.floor(frame / 2) % plan.grain.length])} style={{ position: 'absolute', left: 0, top: 0, width: W, height: H, objectFit: 'cover', opacity: 0.05, mixBlendMode: 'overlay' }} /> : null}
      <AbsoluteFill style={{ backgroundColor: '#000', opacity: Math.max(startFade, endFade) }} />
      {plan.voice.map((v, i) => <Sequence key={i} from={Math.round(v.s * fps)}><Audio src={staticFile(v.src)} /></Sequence>)}
      {plan.music ? (
        <Audio src={staticFile(plan.music)} volume={(f) => {
          const tt = f / fps;
          return plan.musicVolume * Math.max(0, Math.min(1, tt / 1.5, (durationInFrames / fps - tt) / 2)) * (speaking(tt) ? 0.6 : 1);
        }} />
      ) : null}
    </AbsoluteFill>
  );
};
