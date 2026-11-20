#!/usr/bin/env python3
"""The posting caption of a video (owner, 16/11/2026): news/<N>/caption.txt, written by Claude at the picks step and
published beside video.mp4 on renders, so the owner finds it next to the video when downloading it.

Format (UTF-8, English — the channel's language, at most 2000 characters), blocks separated by one blank line:

    <hook title, at most 80 characters>
    <2–4 short sentences describing the video, true to the script>

    #TrueCrime #CrimeStory #ColdCase #shorts #…         (5–8 hashtags)

    Image credits: …                                     (or "Image credits: see credits")

Usage: caption.py <caption.txt>  → prints the problems (exit 1) or "caption OK".
"""
import re, sys

MAX_ALL, MAX_TITLE, TAGS = 2000, 80, (5, 8)
# letters that only Vietnamese uses (ă â đ ê ô ơ ư with tones) and Japanese/Chinese script: iron rule 1, English only
FOREIGN = re.compile('[ăắằẳẵặấầẩẫậđẹẻẽếềểễệỉịọỏốồổỗộơớờởỡợụủưứừửữựỳỵỷỹĂĐƠƯ぀-ヿ一-鿿]')


def check(text):
    """Problems of a caption as short Vietnamese sentences for the owner's issue ([] = fine)."""
    bad = []
    t = text.replace('\r\n', '\n').strip()
    if not t:
        return ['caption.txt trống']
    if len(t) > MAX_ALL:
        bad.append(f'dài {len(t)} ký tự, tối đa {MAX_ALL}')
    if FOREIGN.search(t):
        bad.append(f'có chữ không phải tiếng Anh ("{FOREIGN.search(t).group(0)}"): lời đăng phải bằng tiếng Anh')
    blocks = [b.strip() for b in re.split(r'\n\s*\n', t) if b.strip()]
    if len(blocks) < 3:
        return bad + ['cần 3 phần cách nhau một dòng trống: tiêu đề + mô tả, hashtag, "Image credits: …"']
    head, tags, credit = '\n'.join(blocks[:-2]).split('\n'), blocks[-2].split(), blocks[-1]
    title = head[0].strip()
    if len(title) > MAX_TITLE:
        bad.append(f'tiêu đề dài {len(title)} ký tự, tối đa {MAX_TITLE}')
    if not any(l.strip() for l in head[1:]):
        bad.append('thiếu 2–4 câu mô tả video dưới tiêu đề')
    if not all(re.fullmatch(r'#\w+', w) for w in tags):
        bad.append('phần thứ hai chỉ chứa hashtag (#Word, không dấu cách bên trong)')
    elif not TAGS[0] <= len(tags) <= TAGS[1]:
        bad.append(f'có {len(tags)} hashtag, cần {TAGS[0]}–{TAGS[1]}')
    if not credit.startswith('Image credits:'):
        bad.append('phần cuối phải bắt đầu bằng "Image credits:"')
    return bad


if __name__ == '__main__':
    problems = check(open(sys.argv[1], encoding='utf-8').read())
    print('\n'.join(problems) or 'caption OK')
    sys.exit(1 if problems else 0)
