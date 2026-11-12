// Local stills of a news video (optional check before pushing picks.json).
// Usage: node scripts/news/stills.mjs <plan.json> <public_dir> <out_prefix> <t1> [t2 ...]   (seconds, half size)
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
const [planFile, publicDir, prefix, ...ts] = process.argv.slice(2);
const inputProps = JSON.parse(fs.readFileSync(planFile, 'utf8'));
const serveUrl = await bundle({ entryPoint: path.resolve('src/news/index.ts'), publicDir: path.resolve(publicDir) });
const chromiumOptions = { gl: 'swiftshader' };
const composition = await selectComposition({ serveUrl, id: 'NewsV', inputProps, chromiumOptions });
for (const t of ts) {
  const frame = Math.min(composition.durationInFrames - 1, Math.round(Number(t) * composition.fps));
  await renderStill({ serveUrl, composition, inputProps, frame, output: `${prefix}_${t}.png`, chromiumOptions, scale: 0.5 });
  console.log(`${prefix}_${t}.png`);
}
