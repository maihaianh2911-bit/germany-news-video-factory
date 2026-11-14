#!/usr/bin/env python3
"""Minimal client for the 11labs.id.vn external API (stdlib only).

Commands:
  balance                         -> print quota info
  voices [--language German]    -> write voices markdown list
  tts --text-file F --out DIR [--voice ID] [--speed 1.0]
       voice ids starting with "clone_" are sent to /clone.php, others to /tts.php

Safety rules (from the provider docs):
  * the key is read from the VN11_API_KEY env var only, never printed;
  * a create request is sent at most once; after that we only poll (only an explicit 429 "too many requests",
    which means the job was not accepted, is sent again);
  * 401/403 stop immediately (bad key / no quota); 429/500/502/503/504 and network errors on polling are retried
    until the job's time limit: a job that was paid for is not given up because of one bad answer;
  * the balance shown before and after a job is information only: when it cannot be read the job goes on;
  * GET requests (balance, status, downloads) are retried on network errors and unreadable answers; the POST that
    creates a job is never retried (after a timeout it may have been received and billed);
  * results are downloaded right away (MP3 kept only ~6 h on the provider side).
"""
import argparse, http.client, json, os, sys, time, uuid, urllib.request, urllib.error, urllib.parse

BASE = os.environ.get('VN11_API_BASE', 'https://11labs.id.vn/api/external/v1')
KEY = os.environ.get('VN11_API_KEY', '')
UA = 'video-factory/0.1'


def die(msg, code=1):
    print(f'::error::{msg}')
    sys.exit(code)


CREATE_TRIES, POLL_WAIT, RETRY_WAIT = 3, 4, 10   # seconds; module values so tests can shorten them
NET = (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException)   # HTTPError is caught first


def req(method, path, data=None, headers=None, raw=False, timeout=60, tries=None):
    tries = tries or (4 if method == 'GET' else 1)
    h = {'x-api-key': KEY, 'User-Agent': UA}
    h.update(headers or {})
    for i in range(tries):
        r = urllib.request.Request(BASE.rstrip('/') + '/' + path.lstrip('/'), data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                body = resp.read()
                return resp.status, (body if raw else json.loads(body.decode('utf-8') or '{}'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')
            try:
                j = json.loads(body)
            except Exception:
                j = {'error': body[:300]}
            return e.code, j
        except (*NET, ValueError) as e:   # ValueError: JSONDecodeError, UnicodeDecodeError
            if i == tries - 1:
                raise
            print(f'::warning::11labs {method} {path.split("?")[0]}: {type(e).__name__}, thử lại', flush=True)
            time.sleep(5 * (i + 1))


def multipart(fields):
    b = uuid.uuid4().hex
    out = b''
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n'.encode() + str(v).encode('utf-8') + b'\r\n'
    out += f'--{b}--\r\n'.encode()
    return out, {'Content-Type': f'multipart/form-data; boundary={b}'}


def check_create(code, j):
    if code == 401: die('11labs: API key sai hoặc hết hạn (401). Kiểm tra secret VN11_API_KEY.')
    if code == 403: die('11labs: hết hạn mức (403). Cần nạp thêm ký tự.')
    if code >= 400: die(f'11labs: lỗi khi tạo job ({code}): {j.get("error", j)}')
    if not j.get('job_id'): die(f'11labs: không nhận được job_id: {j}')


def download(url, dest, tries=4):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(r, timeout=120) as resp:
                body = resp.read()
            break
        except urllib.error.HTTPError as e:
            if (e.code < 500 and e.code != 429) or i == tries - 1: raise
            time.sleep(5 * (i + 1))
        except NET:
            if i == tries - 1: raise
            print('::warning::11labs: tải file lỗi mạng, thử lại', flush=True)
            time.sleep(5 * (i + 1))
    with open(dest, 'wb') as f:
        f.write(body)
    return os.path.getsize(dest)


def cmd_balance(_, soft=False):
    """Quota info. soft=True (around a voice job): a balance that cannot be read is a warning and {}, never an error."""
    try:
        code, j = req('GET', 'user.php')
    except (*NET, ValueError) as e:
        if not soft: raise
        print(f'::warning::11labs: không đọc được số dư ({type(e).__name__}), vẫn làm tiếp', flush=True)
        return {}
    if code != 200:
        if not soft: die(f'11labs balance lỗi ({code}): {j.get("error", j)}')
        print(f'::warning::11labs: không đọc được số dư ({code}), vẫn làm tiếp', flush=True)
        return {}
    info = {k: j.get(k) for k in ('quota_total', 'quota_used', 'remaining_quota', 'expires_at')}
    print(json.dumps(info, ensure_ascii=False))
    return info


def cmd_voices(a):
    rows, page = [], 1
    while True:
        q = f'voices.php?page={page}&page_size=200'
        if a.language: q += f'&language={urllib.parse.quote(a.language)}'
        code, j = req('GET', q)
        if code != 200: die(f'11labs voices lỗi ({code}): {j.get("error", j)}')
        rows += j.get('voices', [])
        if not j.get('has_more'): break
        page += 1
        if page > 20: break
    code, jc = req('GET', 'voices.php?provider=clone&page_size=200')
    clones = jc.get('voices', []) if code == 200 else []
    lines = ['## Giọng clone của bạn', '', '| Tên | voice_id |', '|---|---|']
    lines += [f"| {v.get('name')} | `{v.get('voice_id')}` |" for v in clones] or ['| (không có) | |']
    lines += ['', f'## Giọng {a.language or "tất cả"} ({len(rows)})', '', '| Tên | Nhà cung cấp | voice_id | Nghe thử |', '|---|---|---|---|']
    for v in rows[:300]:
        lines.append(f"| {v.get('name')} | {v.get('provider')} | `{v.get('voice_id')}` | {('[nghe](' + v['preview_url'] + ')') if v.get('preview_url') else ''} |")
    md = '\n'.join(lines)
    open(a.out, 'w').write(md)
    print(f'{len(clones)} clone voices, {len(rows)} voices')


def cmd_tts(a):
    text = open(a.text_file, encoding='utf-8').read().strip()
    if not text: die('Văn bản rỗng')
    os.makedirs(a.out, exist_ok=True)
    before = cmd_balance(None, soft=True)
    voice = a.voice or os.environ.get('VN11_VOICE_ID') or ''
    for i in range(CREATE_TRIES):
        if voice.startswith('clone_'):
            body, h = multipart({'text': text, 'clone_voice_id': voice})
            code, j = req('POST', 'clone.php', data=body, headers=h, timeout=120)
        else:
            payload = {'text': text, 'voice_settings': {'language': 'German', 'speed': a.speed, 'normalization': False, 'expressive_optimize': False}}
            if voice: payload['voice_id'] = voice
            code, j = req('POST', 'tts.php', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, timeout=120)
        if code != 429 or i == CREATE_TRIES - 1: break
        # 429 = refused before a job exists, so asking again cannot bill twice (unlike a timeout or a 502/504)
        print(f'::warning::11labs: quá nhiều yêu cầu (429), chờ rồi gửi lại ({i + 1}/{CREATE_TRIES})', flush=True)
        time.sleep(RETRY_WAIT * (i + 1))
    check_create(code, j)
    job = j['job_id']
    json.dump({'job_id': job, 'voice': voice, 'create_response': j}, open(os.path.join(a.out, 'job.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'job {job} created (voice={voice or "default"})')
    t0 = time.time(); st = {}
    while time.time() - t0 < a.timeout:
        time.sleep(POLL_WAIT)
        try:
            code, st = req('GET', f'status.php?job_id={urllib.parse.quote(job)}')
        except (*NET, ValueError) as e:   # the job is paid for: keep asking until the time limit
            print(f'::warning::11labs status: {type(e).__name__}, hỏi lại', flush=True)
            code, st = 503, {}
        if code in (429, 500, 502, 503, 504): time.sleep(RETRY_WAIT); continue
        if code != 200: die(f'11labs status lỗi ({code}): {st.get("error", st)}')
        s = st.get('status')
        if s == 'completed': break
        if s == 'failed': die(f'11labs job {job} failed: {st}')
    else:
        die(f'11labs job {job} chưa xong sau {a.timeout}s (job vẫn được lưu, có thể lấy tiếp).')
    n = download(st['download_url'], os.path.join(a.out, 'voice.mp3'))
    if st.get('srt_url'):
        try: download(st['srt_url'], os.path.join(a.out, 'voice.srt'))
        except Exception as e: print(f'::warning::không tải được SRT: {e}')
    after = cmd_balance(None, soft=True)
    used = (before['remaining_quota'] - after['remaining_quota']) if before.get('remaining_quota') is not None and after.get('remaining_quota') is not None else None
    usage = {'job_id': job, 'voice': voice, 'chars_in_text': len(text), 'quota_used_this_job': used, 'remaining_quota': after.get('remaining_quota'), 'mp3_bytes': n}
    json.dump(usage, open(os.path.join(a.out, 'usage.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(usage, ensure_ascii=False))
    return usage


if __name__ == '__main__':
    import urllib.parse
    if not KEY: die('Thiếu secret VN11_API_KEY')
    p = argparse.ArgumentParser(); sp = p.add_subparsers(dest='cmd', required=True)
    sp.add_parser('balance')
    v = sp.add_parser('voices'); v.add_argument('--language', default='German'); v.add_argument('--out', default='voices.md')
    t = sp.add_parser('tts'); t.add_argument('--text-file', required=True); t.add_argument('--out', required=True)
    t.add_argument('--voice', default=''); t.add_argument('--speed', type=float, default=1.0); t.add_argument('--timeout', type=int, default=900)
    a = p.parse_args()
    {'balance': cmd_balance, 'voices': cmd_voices, 'tts': cmd_tts}[a.cmd](a)
