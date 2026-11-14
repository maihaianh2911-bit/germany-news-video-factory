import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Audio, Img, Sequence, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

// Vertical (1080×1920) German news short in the style of the owner's sample (14/11/2026): a dark starry night,
// a header top left (cover picture, headline in capitals, an italic line, the channel name in typewriter type),
// one landscape picture panel with rounded corners (slow camera moves, cross-fades) and serif subtitles below it;
// quotes sit in a white box. It opens with a strip of the video's pictures sliding in under the typed channel
// name; the cover picture is singled out and flies into the header. The plan (props) is written by
// scripts/news/build.py; see AGENT_NEWS.md.
type Cam = { z: number; x: number; y: number };
type Print = { src: string; w: number; h: number };
type Thumb = { src: string; w: number; h: number; x: number; y: number };
export type Pic = { src: string; w: number; h: number; s: number; e: number; from: Cam; to: Cam; tag?: string; credit?: string;
  pair?: { left: Print & { caption: string[] }; right: Print } }; // pair: two framed prints instead of a full-panel picture
export type Pair = { s: number; e: number; left: { src: string; w: number; h: number; caption: string[] }; right: { src: string; w: number; h: number }; credit?: string };
export type ChapterV = { s: number; e: number; num: string; label: string; title: string; desc: string[]; pics: Pic[] };
export type SubV = { s: number; e: number; text: string; box?: boolean };
export type HeadV = { title: string; sub: string; channel: string; cover: Thumb | null };
type FontChunk = { family: string; file: string; range: string; style?: string };
export type PlanV = { duration: number; chapters: ChapterV[]; subs: SubV[]; voice: { s: number; src: string }[]; music: string | null; musicVolume: number;
  fonts: FontChunk[]; head?: HeadV; intro?: Thumb[]; showChapters?: boolean };

const W = 1080, H = 1920;
export const PX = 40, PY = 520, PW = 1000, PH = 750; // picture panel (4:3); keep in step with preview.py and sheet.py
const SUB_Y = 1318;                                   // top of the subtitle block; the bottom ~450 px stay free for the platform
const HEAD = { x: 64, y: 170, w: 196, h: 294 };        // cover picture in the header
const BG = '#07080c', WHITE = '#f2f0ec', GREY = '#a3a3a8';
const SERIF = '"Source Serif 4", serif', SANS = '"Source Sans 3", sans-serif', MONO = '"Courier Prime", "Courier New", monospace';
const INTRO = 3.4; // seconds of the opening (the voice already speaks over it)
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const ease = (x: number) => { const p = clamp01(x); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;

let fontsLoading: Promise<void> | null = null;
const useFonts = (fonts: FontChunk[], text: string) => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    (fontsLoading ??= (async () => {
      for (const f of fonts)
        document.fonts.add(new FontFace(f.family, `url(${staticFile(f.file)}) format('woff2')`, { weight: '100 900', style: f.style || 'normal', unicodeRange: f.range }));
      await Promise.all([700, 500, 400].flatMap((wt) => [document.fonts.load(`${wt} 60px ${SERIF}`, text), document.fonts.load(`${wt} 40px ${SANS}`, text)])
        .concat([document.fonts.load(`italic 400 34px ${SERIF}`, text), document.fonts.load(`400 32px ${MONO}`, text)]));
    })()).then(() => continueRender(h)).catch((e) => cancelRender(e));
  }, [h, fonts, text]);
};

// twinkling stars, the same sky in every video
const STARS = (() => {
  let s = 7; const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  return Array.from({ length: 230 }, () => ({ x: r() * W, y: r() * H, size: 1.3 + r() * r() * 3.4, a: 0.3 + r() * 0.65, sp: 0.6 + r() * 1.8, ph: r() * 6.3 }));
})();
const Sky: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 38%, #10131c 0%, ${BG} 70%)` }}>
    {STARS.map((st, i) => (
      <div key={i} style={{ position: 'absolute', left: st.x, top: st.y, width: st.size, height: st.size, borderRadius: '50%', background: '#fff',
        opacity: st.a * (0.55 + 0.45 * Math.sin(t * st.sp + st.ph)) }} />
    ))}
  </AbsoluteFill>
);

// one picture filling the panel, moving from `from` to `to` (cover-fit, clamped so no edge shows)
const PicView: React.FC<{ p: Pic; t: number }> = ({ p, t }) => {
  if (p.pair) return <PairView p={{ s: p.s, e: p.e, left: p.pair.left, right: p.pair.right }} t={t} />;
  const k = ease((t - p.s) / Math.max(0.5, p.e - p.s));
  const z = lerp(p.from.z, p.to.z, k), x = lerp(p.from.x, p.to.x, k), y = lerp(p.from.y, p.to.y, k);
  const c = Math.max(PW / p.w, PH / p.h) * z, dw = p.w * c, dh = p.h * c;
  const left = Math.min(0, Math.max(PW - dw, PW / 2 - x * dw)), top = Math.min(0, Math.max(PH - dh, PH / 2 - y * dh));
  return <Img src={staticFile(p.src)} style={{ position: 'absolute', left, top, width: dw, height: dh, maxWidth: 'none' }} />;
};

// portrait photo + document as framed prints on a dark background (sizes in panel pixels; preview.py mirrors them)
export const PAIR = { left: { bw: 280, x: 95 }, right: { bw: 320, x: 530 }, top: 80, room: 250 };
const PairView: React.FC<{ p: Pair; t: number }> = ({ p, t }) => {
  const k = ease((t - p.s) / Math.max(0.5, p.e - p.s));
  const z = 1 + 0.05 * k;
  const lh = (PAIR.left.bw * p.left.h) / p.left.w;
  const top = Math.min(PAIR.top, PH - PAIR.room - lh); // tall portraits move up so the caption clears the credit line
  const frame = (src: string, w: number, h: number, bw: number, x: number, y: number, rot: number, d: number) => {
    const a = easeOut((t - p.s - d) / 0.9);
    return (
      <div style={{ position: 'absolute', left: x, top: y + (1 - a) * 24, width: bw + 20, opacity: a, transform: `rotate(${rot}deg)`,
        background: '#efe7d6', padding: 10, boxShadow: '0 24px 50px rgba(0,0,0,.55), 0 4px 10px rgba(0,0,0,.4)' }}>
        <Img src={staticFile(src)} style={{ display: 'block', width: bw, height: (bw * h) / w }} />
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ transform: `scale(${z})`, transformOrigin: '50% 45%' }}>
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 40%, #23252e 0%, #14151b 60%, #0c0d12 100%)' }} />
      {frame(p.left.src, p.left.w, p.left.h, PAIR.left.bw, PAIR.left.x, top, -2.2, 0)}
      {frame(p.right.src, p.right.w, p.right.h, PAIR.right.bw, PAIR.right.x, top - 40, 1.8, 0.35)}
      <div style={{ position: 'absolute', left: PAIR.left.x - 20, top: top + lh + 50, width: PAIR.left.bw + 60, textAlign: 'center', opacity: easeOut((t - p.s - 0.7) / 0.8) }}>
        <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: Math.min(40, Math.floor((PAIR.left.bw + 60) / (p.left.caption[0].length * 0.56))), color: WHITE }}>{p.left.caption[0]}</div>
        <div style={{ fontFamily: SERIF, fontStyle: 'italic', fontWeight: 400, fontSize: 24, color: GREY, marginTop: 4 }}>{p.left.caption[1]}</div>
      </div>
    </AbsoluteFill>
  );
};

// a picture cut to the cover's tall format, centred on (x, y)
const ThumbImg: React.FC<{ th: Thumb; style?: React.CSSProperties }> = ({ th, style }) => (
  <Img src={staticFile(th.src)} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: `${th.x * 100}% ${th.y * 100}%`, display: 'block', ...style }} />
);

const Header: React.FC<{ head: HeadV; t: number; intro: boolean }> = ({ head, t, intro }) => {
  const a = (d: number) => (intro ? easeOut((t - INTRO + 0.45 - d) / 0.6) : 1);
  const titleRows = head.title.split('\n');
  const longest = Math.max(...titleRows.map((r) => r.length));
  const tx = HEAD.x + HEAD.w + 40;
  return (
    <>
      {head.cover && (!intro || t >= INTRO - 0.25) ? (
        <div style={{ position: 'absolute', left: HEAD.x, top: HEAD.y, width: HEAD.w, height: HEAD.h, borderRadius: 8, overflow: 'hidden',
          border: '2px solid rgba(255,255,255,.22)', boxShadow: '0 10px 30px rgba(0,0,0,.6)' }}><ThumbImg th={head.cover} /></div>
      ) : null}
      <div style={{ position: 'absolute', left: head.cover ? tx : HEAD.x, top: HEAD.y + 26, right: 56 }}>
        <div style={{ opacity: a(0), transform: `translateY(${(1 - a(0)) * 12}px)` }}>
          {titleRows.map((r, i) => (
            <div key={i} style={{ fontFamily: SANS, fontWeight: 700, fontSize: Math.min(44, Math.floor(700 / (Math.max(10, longest) * 0.64))), lineHeight: 1.38,
              color: WHITE, textTransform: 'uppercase', letterSpacing: '0.01em', whiteSpace: 'nowrap' }}>{r}</div>
          ))}
        </div>
        {head.sub ? <div style={{ marginTop: 34, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 400, fontSize: 34, color: '#d4d2cc', opacity: a(0.15), whiteSpace: 'nowrap' }}>{head.sub}</div> : null}
        {head.channel ? <div style={{ marginTop: 26, fontFamily: MONO, fontSize: 31, color: GREY, letterSpacing: '0.08em', opacity: a(0.3), whiteSpace: 'nowrap' }}>{head.channel}</div> : null}
      </div>
    </>
  );
};

// the opening: typed channel name, a strip of the video's pictures, the cover flies into the header
const Intro: React.FC<{ head: HeadV; thumbs: Thumb[]; t: number }> = ({ head, thumbs, t }) => {
  if (t >= INTRO || !thumbs.length) return null;
  const TW = 214, TH = 321, GAP = 24, CY = 870;
  const ci = 8, strip = Array.from({ length: 13 }, (_, i) => (i === ci && head.cover ? head.cover : thumbs[(i + 3) % thumbs.length]));
  const slide = easeOut(t / 2.0);
  const off = lerp(1700, 0, slide);                           // the strip slides in from the right and stops on the cover
  const pick = easeOut((t - 1.7) / 0.5), gone = clamp01((t - 2.25) / 0.35), fly = ease((t - 2.5) / 0.75);
  const typed = head.channel.slice(0, Math.max(0, Math.floor((t - 0.15) / 0.085)));
  const cursor = Math.floor(t * 2.5) % 2 === 0 || typed.length < head.channel.length;
  return (
    <AbsoluteFill>
      {head.channel ? (
        <div style={{ position: 'absolute', left: 0, right: 0, top: 500, textAlign: 'center', fontFamily: MONO, fontSize: 36, color: GREY, letterSpacing: '0.1em',
          opacity: 1 - clamp01((t - 2.3) / 0.4) }}>{typed}<span style={{ opacity: cursor ? 1 : 0 }}>_</span></div>
      ) : null}
      {strip.map((th, i) => {
        const isCover = i === ci;
        const cx = W / 2 + (i - ci) * (TW + GAP) + off;
        let x = cx - TW / 2, y = CY - TH / 2, w = TW, h = TH;
        if (isCover) {
          const sc = 1 + 0.08 * pick * (1 - fly);
          w = lerp(TW * sc, HEAD.w, fly); h = lerp(TH * sc, HEAD.h, fly);
          x = lerp(cx - (TW * sc) / 2, HEAD.x, fly); y = lerp(CY - (TH * sc) / 2, HEAD.y, fly);
        }
        if (x > W + 40 || x + w < -40) return null;
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: 8, overflow: 'hidden',
            opacity: isCover ? 1 : (1 - 0.6 * pick) * (1 - gone),
            border: isCover ? `${lerp(2, 3, pick * (1 - fly))}px solid rgba(255,255,255,${0.22 + 0.6 * pick * (1 - fly)})` : '2px solid rgba(255,255,255,.12)',
            boxShadow: '0 14px 34px rgba(0,0,0,.6)', zIndex: isCover ? 2 : 1 }}>
            <ThumbImg th={th} style={{ filter: isCover ? 'none' : `grayscale(${pick})` }} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const Subtitle: React.FC<{ sub: SubV; a: number }> = ({ sub, a }) => {
  const rows = sub.text.split('\n');
  const longest = Math.max(...rows.map((x) => x.length));
  const style: React.CSSProperties = { position: 'absolute', left: 50, right: 50, top: SUB_Y, textAlign: 'center', opacity: a, transform: `translateY(${(1 - a) * 8}px)` };
  if (sub.box) // a quote: dark text on a white box, as in the sample
    return (
      <div style={style}>
        <div style={{ display: 'inline-block', background: '#f4f3f0', padding: '10px 22px 12px', borderRadius: 3, boxShadow: '0 6px 24px rgba(0,0,0,.45)' }}>
          {rows.map((l, i) => (
            <div key={i} style={{ fontFamily: SANS, fontWeight: 500, fontSize: Math.min(40, Math.floor(900 / (longest * 0.5))), lineHeight: 1.35, color: '#101114', whiteSpace: 'nowrap' }}>{l}</div>
          ))}
        </div>
      </div>
    );
  return (
    <div style={style}>
      {rows.map((l, i) => (
        <div key={i} style={{ fontFamily: SERIF, fontWeight: 400, fontSize: Math.min(47, Math.floor(970 / (longest * 0.5))), lineHeight: 1.5, color: WHITE,
          whiteSpace: 'nowrap', textShadow: '0 2px 14px rgba(0,0,0,.7)' }}>{l}</div>
      ))}
    </div>
  );
};

export const NewsV: React.FC<PlanV> = (plan) => {
  const head: HeadV = plan.head || { title: '', sub: '', channel: '', cover: null };
  useFonts(plan.fonts, head.title + head.sub + head.channel + '_' + plan.chapters.map((c) => c.num + c.title + c.pics.map((p) => (p.tag || '') + (p.credit || '') + (p.pair ? p.pair.left.caption.join('') : '')).join('')).join('') + plan.subs.map((s) => s.text).join(''));
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  if (!plan.chapters.length) return <AbsoluteFill style={{ backgroundColor: BG }} />;
  const intro = !!(plan.intro && plan.intro.length);
  const ci = Math.max(0, plan.chapters.findIndex((c) => t >= c.s && t < c.e));
  const ch = plan.chapters[ci] || plan.chapters[plan.chapters.length - 1];
  const prev = ci > 0 ? plan.chapters[ci - 1] : null;
  const X = 0.7; // cross-fade between pictures
  const inA = ci === 0 ? 1 : easeOut((t - ch.s) / X);
  const visible = (c: ChapterV) => c.pics.filter((p) => t >= p.s - X && t < p.e + X);
  const picLayer = (c: ChapterV, key: string) => (
    <AbsoluteFill key={key}>
      {visible(c).map((p, i) => <AbsoluteFill key={i} style={{ opacity: clamp01((t - (p.s - X)) / X) }}><PicView p={p} t={t} /></AbsoluteFill>)}
    </AbsoluteFill>
  );
  const curPic = ch.pics.find((p) => t >= p.s && t < p.e) || ch.pics[ch.pics.length - 1];
  // the label inside the picture: the picture's tag, or the chapter title at the start of a chapter when chapters are shown
  const chapterTag = plan.showChapters && t < ch.s + 3 ? `${ch.num} · ${ch.title}` : '';
  const tag = chapterTag || curPic?.tag, credit = curPic?.credit;
  const tagA = chapterTag ? Math.min(easeOut((t - ch.s - 0.2) / 0.6), clamp01((ch.s + 3 - t) / 0.4)) : inA;
  const sub = plan.subs.find((s) => t >= s.s - 0.1 && t < s.e + 0.25);
  const subA = sub ? Math.min(clamp01((t - (sub.s - 0.1)) / 0.25), clamp01((sub.e + 0.25 - t) / 0.25)) : 0;
  const panelA = intro ? easeOut((t - INTRO + 0.4) / 0.6) : 1;
  const endFade = clamp01((t - (plan.duration - 1.6)) / 1.6);
  const startFade = 1 - clamp01(t / (intro ? 0.4 : 0.8));
  const speaking = (tt: number) => plan.subs.some((s) => tt >= s.s - 0.2 && tt < s.e + 0.3);
  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      <Sky t={t} />
      {/* picture panel */}
      {panelA > 0 ? (
        <div style={{ position: 'absolute', left: PX, top: PY, width: PW, height: PH, borderRadius: 14, overflow: 'hidden', background: '#0d0e13',
          opacity: panelA, transform: `translateY(${(1 - panelA) * 18}px)`, boxShadow: '0 24px 70px rgba(0,0,0,.65)' }}>
          {prev && t < ch.s + X ? picLayer(prev, 'p') : null}
          <AbsoluteFill style={{ opacity: inA }}>{picLayer(ch, 'c')}</AbsoluteFill>
          <AbsoluteFill style={{ boxShadow: 'inset 0 0 70px rgba(0,0,0,.42)', borderRadius: 14 }} />
          {credit ? <AbsoluteFill style={{ background: 'linear-gradient(180deg, rgba(0,0,0,0) 82%, rgba(0,0,0,.5) 100%)' }} /> : null}
          {tag ? (
            <div style={{ position: 'absolute', left: 30, right: 30, top: 44, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 46,
              color: 'rgba(255,255,255,.78)', letterSpacing: '0.02em', textShadow: '0 2px 16px rgba(0,0,0,.55)', opacity: tagA }}>{tag}</div>
          ) : null}
          {credit ? (
            <div style={{ position: 'absolute', left: 28, bottom: 18, right: 28, fontFamily: SANS, fontWeight: 400, fontSize: 19, color: 'rgba(235,235,235,.66)',
              letterSpacing: '0.01em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', opacity: inA }}>{credit}</div>
          ) : null}
        </div>
      ) : null}
      <Header head={head} t={t} intro={intro} />
      {intro ? <Intro head={head} thumbs={plan.intro || []} t={t} /> : null}
      {sub ? <Subtitle sub={sub} a={subA} /> : null}
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
