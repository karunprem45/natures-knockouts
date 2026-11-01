"""Render site/keynote.html to a 16:9 MP4 (1920x1080, 30 fps) with a synthesized background score.

Frames: renderAt(t) is called for every frame time, so the video matches the page exactly. The timeline is split
into segments rendered by parallel browser workers, then joined and re-encoded once (CRF 24, about 25 MB).
Score: generated here with numpy (pad, arpeggio, a pulse under the results, hits where the page asks for them
via HITS and PULSE); no samples, nothing downloaded. Needs playwright, imageio, imageio-ffmpeg and Google Chrome.
Usage: .venv/bin/python site/make_video.py
"""
import pathlib
import subprocess
import sys
import wave
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGES = {"keynote": ("null-hypothesis-keynote.mp4", "null-hypothesis-keynote-thumbnail.png")}
FPS, SR, WORKERS = 30, 44100, 6
BEAT = 60 / 90  # 90 bpm
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def open_page(p, name):
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto((HERE / f"{name}.html").as_uri() + "?manual=1")
    return browser, page


def render_segment(args):
    name, k, f0, f1 = args
    seg = HERE / f"_seg{k}.mp4"
    with sync_playwright() as p:
        browser, page = open_page(p, name)
        writer = imageio.get_writer(seg, fps=FPS, codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=8)
        for f in range(f0, f1):
            page.evaluate(f"renderAt({f / FPS})")
            writer.append_data(np.asarray(Image.open(BytesIO(page.screenshot(type="png"))).convert("RGB")))
        writer.close()
        browser.close()
    return seg


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def score(dur, hits, pulse):
    n = int(dur * SR)
    t = np.arange(n) / SR
    L, R = np.zeros(n), np.zeros(n)
    chords = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]  # Am F C G
    span = 8 * BEAT
    # pad: each chord fades in and out with a raised cosine, detuned pair for width
    for k in range(int(dur / span) + 2):
        root, tri = chords[k % 4]
        env = np.clip(1 - np.abs((t - (k * span + span / 2)) / (span / 2 + 0.8)), 0, 1)
        env = 0.5 - 0.5 * np.cos(np.pi * env)
        if not env.any():
            continue
        for m, g in [(root, 0.22), (root + 12, 0.10)] + [(x, 0.07) for x in tri]:
            f = midi(m)
            L += g * env * np.sin(2 * np.pi * f * 0.999 * t)
            R += g * env * np.sin(2 * np.pi * f * 1.001 * t + 0.3)
    # arpeggio: eighth-note plucks through the chord tones, like a sequence being read
    arp_on = np.clip((t - 7) / 4, 0, 1) * (0.6 + 0.4 * np.clip((t - 17) / 4, 0, 1))
    step = BEAT / 2
    pl = int(0.5 * SR)
    pt = np.arange(pl) / SR
    for i in range(int(dur / step)):
        s = i * step
        if s < 7 or s > dur - 3:
            continue
        _, tri = chords[int(s // span) % 4]
        f = midi(tri[[0, 1, 2, 1][i % 4]] + 12)
        note = (np.sin(2 * np.pi * f * pt) + 0.15 * np.sin(6 * np.pi * f * pt)) * np.exp(-pt / 0.32)  # soft bell
        a = int(s * SR)
        b = min(n, a + pl)
        g = 0.06 * arp_on[a]
        pan = 0.5 + 0.3 * np.sin(i * 0.7)
        L[a:b] += g * (1 - pan) * 2 * note[: b - a]
        R[a:b] += g * pan * 2 * note[: b - a]
    # pulse: a soft kick on every beat while the results play
    kl = int(0.35 * SR)
    kt = np.arange(kl) / SR
    kick = np.sin(2 * np.pi * (45 * kt + 60 * 0.04 * (1 - np.exp(-kt / 0.04)))) * np.exp(-kt / 0.12)
    rng = np.random.default_rng(1)
    tick = rng.standard_normal(int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR / 0.008)
    for i in range(int(dur / BEAT)):
        s = i * BEAT
        if pulse[0] <= s < pulse[1]:
            for src, off, g in [(kick, 0, 0.14)]:
                a = int((s + off) * SR)
                b = min(n, a + len(src))
                L[a:b] += g * src[: b - a]
                R[a:b] += g * src[: b - a]
    # hits: a low boom with a short glitch, plus a rising whoosh into it
    for s, g in hits:
        hl = int(2.5 * SR)
        ht = np.arange(hl) / SR
        boom = np.sin(2 * np.pi * (38 * ht + 40 * 0.08 * (1 - np.exp(-ht / 0.08)))) * np.exp(-ht / 0.6)
        glitch = rng.standard_normal(hl) * np.exp(-ht / 0.03) * 0.04
        a = int(s * SR)
        b = min(n, a + hl)
        L[a:b] += g * (boom + glitch)[: b - a]
        R[a:b] += g * (boom - glitch)[: b - a]
        wl = int(0.8 * SR)
        w = rng.standard_normal(wl) * np.linspace(0, 1, wl) ** 3 * 0.03 * g
        a0 = max(0, a - wl)
        L[a0:a] += w[wl - (a - a0):]
        R[a0:a] += w[wl - (a - a0):]
    # echo on the whole mix, then fades and normalise
    d = int(BEAT * 0.75 * SR)
    for ch in (L, R):
        ch[d:] += 0.32 * ch[:-d].copy()
        ch[2 * d:] += 0.12 * ch[:-2 * d].copy()
    fade = np.clip(t / 2, 0, 1) * np.clip((dur - t) / 4, 0, 1)
    mix = np.stack([L * fade, R * fade], axis=1)
    return (mix / np.abs(mix).max() * 0.8 * 32767).astype(np.int16)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "keynote"
    OUT, THUMB = (HERE / f for f in PAGES[name])
    with sync_playwright() as p:
        browser, page = open_page(p, name)
        dur, hits, pulse = page.evaluate("[DURATION, HITS, PULSE]")
        page.evaluate(f"renderAt(4)")
        page.screenshot(path=str(THUMB))
        browser.close()
    total = int(dur * FPS)
    cuts = np.linspace(0, total, WORKERS + 1).astype(int)
    with ProcessPoolExecutor(WORKERS) as ex:
        segs = list(ex.map(render_segment, [(name, k, cuts[k], cuts[k + 1]) for k in range(WORKERS)]))
    lst = HERE / "_segs.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    audio = HERE / "_score.wav"
    with wave.open(str(audio), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(score(dur, hits, pulse).tobytes())
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)], check=True)
    for f in segs + [lst, audio]:
        f.unlink()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB, {dur:.0f} s) and {THUMB.name}")


if __name__ == "__main__":
    main()
