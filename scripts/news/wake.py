#!/usr/bin/env python3
"""Start the Claude task (its API trigger) and tell the issue what happens next.

Usage: wake.py "<why>" [--issue N] [--say TEXT] [--then TEXT] [--tail TEXT]

  why     one line for the task's log (which issue, which step)
  --issue the issue this call is about. With it:
            * when the issue carries a news-busy label added less than 2 hours ago, a Claude session is already
              working on it: the task is not called;
            * one comment is posted: <say> + <then> when Claude was called (or is already on the issue), else
              <say> + a plain note that Claude could not be called and which button to press. So a machine comment
              never promises "Claude sẽ …" when nobody was called.
  --say   what the machine just did (the comment starts with it; 🤖 is added when missing)
  --then  what Claude does next (only said when Claude was called or holds the issue)
  --tail  lines added at the end of the comment either way (links)

The call is tried 3 times (network errors, 429, 5xx). Never fails the workflow: exit code 0 whatever happens.
Needs CLAUDE_TASK_URL and CLAUDE_TASK_TOKEN (repo secrets); for --issue also GH_TOKEN and GH_REPO or
GITHUB_REPOSITORY. There is no hourly run: when the call fails the issue waits for the button "Gọi Claude ngay"
(wake.yml) or a chat.
"""
import argparse, datetime, json, os, subprocess, sys, time, urllib.error, urllib.request

BUSY = 'news-busy'
BUSY_HOURS = 2
TRIES = 3
REPO = os.environ.get('GH_REPO') or os.environ.get('GITHUB_REPOSITORY') or ''
NO_SECRET = 'repo này chưa được nối với tác vụ Claude'
NO_ANSWER = 'Claude không nhận cuộc gọi, có thể đang hết hạn mức'


def busy_fresh(labels, labeled_at, now, hours=BUSY_HOURS):
    """True when the issue carries news-busy and the label was last added less than `hours` ago.
    labels: names on the issue now; labeled_at: ISO times of every "news-busy was added" event; now: aware datetime.
    A label whose time is unknown (no event read) does not count: better one call too many than an issue left."""
    if BUSY not in labels:
        return False
    times = []
    for t in labeled_at:
        try: times.append(datetime.datetime.fromisoformat(t.strip().replace('Z', '+00:00')))
        except ValueError: pass
    return bool(times) and now - max(times) < datetime.timedelta(hours=hours)


def note(reason, issue, repo=None):
    """The plain sentence for the owner when Claude could not be called."""
    return (f'⚠️ Chưa gọi được Claude ({reason}), nên phiếu này đang chờ. Mở trang **Gọi Claude ngay** '
            f'(https://github.com/{repo or REPO}/actions/workflows/wake.yml) rồi bấm **Run workflow**, '
            f'hoặc nhắn Claude trong chat: "làm tiếp phiếu tin tức số {issue}".')


def body(say, then, tail, called, reason, issue, repo=None):
    """The issue comment ('' = nothing to say). called: Claude was called or already holds the issue."""
    parts = [say.strip(), then.strip() if called else note(reason, issue, repo)]
    text = ' '.join(p for p in parts if p)
    if not text:
        return ''
    if not text.startswith('🤖'):
        text = '🤖 ' + text
    return text + ('\n\n' + tail.strip() if tail.strip() else '')


def gh(*a):
    return subprocess.run(['gh', *a], capture_output=True, text=True)


def issue_busy(issue):
    lab = gh('api', f'repos/{REPO}/issues/{issue}', '--jq', '.labels[].name')
    if lab.returncode or BUSY not in lab.stdout.split('\n'):
        return False
    ev = gh('api', '--paginate', f'repos/{REPO}/issues/{issue}/events?per_page=100', '--jq',
            f'.[] | select(.event == "labeled" and .label.name == "{BUSY}") | .created_at')
    if ev.returncode:
        return False
    return busy_fresh([BUSY], ev.stdout.split(), datetime.datetime.now(datetime.timezone.utc))


def call(why, post=None, sleep=time.sleep):
    """Call the task's API trigger. Returns '' when Claude was called, else the reason (Vietnamese, for the owner).
    post(url, token, payload) → (http code, body text) is replaceable for tests."""
    url, token = os.environ.get('CLAUDE_TASK_URL', ''), os.environ.get('CLAUDE_TASK_TOKEN', '')
    if not url or not token:
        print('::warning::Chưa cài CLAUDE_TASK_URL/CLAUDE_TASK_TOKEN: chưa gọi được Claude. Phiếu chờ đến khi thêm hai '
              'secret này rồi bấm Gọi Claude ngay, hoặc làm trong chat.', flush=True)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
                f.write('\n### Chưa gọi được Claude ngay\nThêm secrets `CLAUDE_TASK_URL` và `CLAUDE_TASK_TOKEN` (API trigger '
                        'của tác vụ Claude cho repo này) để Claude bắt đầu ngay khi có việc. Không có lượt chạy mỗi giờ: '
                        'hiện phiếu chờ đến khi bấm **Gọi Claude ngay** hoặc làm trong chat.\n')
        return NO_SECRET
    payload = json.dumps({'text': why[:300]}).encode()
    code = 0
    for i in range(TRIES):
        if i:
            sleep(10 * i)
        code, text = (post or http_post)(url, token, payload)
        if 200 <= code < 300:
            try: session = json.loads(text).get('claude_code_session_url', '')
            except Exception: session = ''
            print(f'wake: Claude đã được gọi ({session})', flush=True)
            return ''
        print(f'::warning::wake: lần {i + 1}/{TRIES} không được (HTTP {code}) {text[:300]}', flush=True)
        if code in (400, 401, 403, 404):   # a wrong URL or token does not get better by trying again
            break
    print(f'::warning::wake: gọi Claude không được (HTTP {code}) — bấm Gọi Claude ngay sau, hoặc làm trong chat', flush=True)
    return NO_ANSWER


def http_post(url, token, payload):
    r = urllib.request.Request(url, data=payload, method='POST', headers={
        'Authorization': f'Bearer {token}', 'anthropic-beta': 'experimental-cc-routine-2026-04-01',
        'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')
    except Exception as e:   # timeout, reset, DNS
        return 0, type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('why'); ap.add_argument('--issue', default=''); ap.add_argument('--say', default='')
    ap.add_argument('--then', default=''); ap.add_argument('--tail', default='')
    a = ap.parse_args()
    issue = a.issue if a.issue.isdigit() and REPO else ''
    if issue and issue_busy(issue):
        print(f'wake: phiếu #{issue} đang có {BUSY} (dưới {BUSY_HOURS} giờ): Claude đang làm, không gọi thêm.', flush=True)
        reason = ''
    else:
        reason = call(a.why)
    if issue:
        text = body(a.say, a.then, a.tail, not reason, reason, issue)
        if text:
            r = gh('issue', 'comment', issue, '--repo', REPO, '--body', text)
            if r.returncode:
                print(f'::warning::wake: không ghi được bình luận lên phiếu #{issue}: {r.stderr.strip()[:300]}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:   # never fail the workflow because of the wake call
        print(f'::warning::wake: {type(e).__name__}: {e}', flush=True)
    sys.exit(0)
