"""ffmpeg for the news-video scripts: the system binary, else the static one from the imageio-ffmpeg wheel
(the apt mirror sometimes hangs on the runners). duration() decodes instead of using ffprobe, which that wheel lacks."""
import shutil, subprocess


def ffmpeg():
    p = shutil.which('ffmpeg')
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(*args):
    subprocess.run([ffmpeg(), '-v', 'error', '-y', *args], check=True)


def duration(path):
    """Length in seconds of an audio file (decoded to 16 kHz mono 16-bit, so it works with any ffmpeg build)."""
    raw = subprocess.run([ffmpeg(), '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', '16000', '-'],
                         check=True, capture_output=True).stdout
    return len(raw) / 32000.0


TRIM = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,'
        'areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse')
