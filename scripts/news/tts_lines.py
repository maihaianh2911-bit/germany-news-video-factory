#!/usr/bin/env python3
"""Voice for a news video: one 11labs job per script line, so every subtitle shows exactly while its line is
spoken. Usage: tts_lines.py <news/N/script.json> <out_dir> [--prev <dir of an earlier run>]

The text sent to 11labs is script.json "tts"[line] when given, else the line with prompts/news_readings.json applied
(respellings for words the German voice misreads, e.g. names and abbreviations; whole words only). Lines whose spoken text did not change are copied
from --prev instead of being read again (saves credits when only a few lines are fixed).
Writes <out_dir>/line_XX.mp3 (silence trimmed at both ends) and lines.json [{i, text, tts, file, duration}].
"""
import argparse, json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import ff
import vn11

PROMPTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'prompts')
READINGS = os.path.join(PROMPTS, 'news_readings.json')
DEFAULT_VOICE = json.load(open(os.path.join(PROMPTS, 'news_voice.json'), encoding='utf-8')).get('default') or ''


def spoken(script, rd=None):
    """Text sent to the voice per line: script "tts" when given, else the line with the readings applied to whole
    words only ("US" → "U S" leaves "USA" alone), longest key first, in one pass (a replacement is not replaced again)."""
    if rd is None:
        rd = {k: v for k, v in json.load(open(READINGS, encoding='utf-8')).items() if not k.startswith('_')}
    pat = re.compile(r'(?<!\w)(' + '|'.join(map(re.escape, sorted(rd, key=len, reverse=True))) + r')(?!\w)') if rd else None
    out = []
    for i, line in enumerate(script['lines'], 1):
        t = (script.get('tts') or {}).get(str(i))
        if not t:
            t = pat.sub(lambda m: rd[m.group(1)], line) if pat else line
        out.append(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script'); ap.add_argument('out'); ap.add_argument('--prev')
    a = ap.parse_args()
    script = json.load(open(a.script, encoding='utf-8'))
    voice = script.get('voice') or DEFAULT_VOICE
    if not voice:
        vn11.die('Chưa chọn giọng đọc tiếng Đức: ghi voice_id vào prompts/news_voice.json ("default") hoặc vào script.json ("voice").')
    prev = {}
    if a.prev and os.path.exists(os.path.join(a.prev, 'lines.json')):
        prev = {(r['tts'], voice): r for r in json.load(open(os.path.join(a.prev, 'lines.json'), encoding='utf-8')) if r.get('voice') == voice}
    os.makedirs(a.out, exist_ok=True)
    rows, read = [], 0
    for i, (text, tts) in enumerate(zip(script['lines'], spoken(script)), 1):
        dst = os.path.join(a.out, f'line_{i:02d}.mp3')
        old = prev.get((tts, voice))
        reuse = bool(old) and os.path.exists(os.path.join(a.prev, old['file']))
        if reuse:
            if os.path.abspath(os.path.join(a.prev, old['file'])) != os.path.abspath(dst):
                shutil.copy(os.path.join(a.prev, old['file']), dst)
        else:
            work = os.path.join(a.out, f'job_{i:02d}'); os.makedirs(work, exist_ok=True)
            tf = os.path.join(work, 'text.txt'); open(tf, 'w', encoding='utf-8').write(tts)
            vn11.cmd_tts(argparse.Namespace(text_file=tf, out=work, voice=voice, speed=1.0, timeout=900))
            ff.run('-i', os.path.join(work, 'voice.mp3'), '-af', ff.TRIM, '-ar', '44100', '-c:a', 'libmp3lame', '-q:a', '2', dst)
            shutil.rmtree(work, ignore_errors=True); read += 1
        rows.append({'i': i, 'text': text, 'tts': tts, 'voice': voice, 'file': os.path.basename(dst), 'duration': round(ff.duration(dst), 3)})
        print(f'line {i}: {rows[-1]["duration"]} s{"" if reuse else " (new)"}', flush=True)
    json.dump(rows, open(os.path.join(a.out, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{read} lines read, {len(rows) - read} reused; {sum(r["duration"] for r in rows):.1f} s of speech')


if __name__ == '__main__':
    if not vn11.KEY:
        vn11.die('Thiếu secret VN11_API_KEY')
    main()
