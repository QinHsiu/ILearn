#!/usr/bin/env python3
"""Build GOAI Demo video from video_1.txt segments.

Usage (repo root, FE+BE up):
  python scripts/build_goai_demo_video.py
  python scripts/build_goai_demo_video.py --force-tts
  python scripts/build_goai_demo_video.py --mux-only
  python scripts/build_goai_demo_video.py --only 08_xiaohong_demo,10_xiaohua_demo
  python scripts/build_goai_demo_video.py --speed 1.25   # after build, or alone with --speed-only
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEG_JSON = ROOT / "doc" / "submit" / "goai_video_segments_fast.json"
CARDS = ROOT / "doc" / "submit" / "demo_cards.html"
WORK = ROOT / "runtime_evidence" / "goai_video_build_runtime"
AUDIO_DIR = WORK / "audio"
VIDEO_DIR = WORK / "video_raw"
MUX_DIR = WORK / "muxed"
FINAL_1080 = ROOT / "runtime_evidence" / "demo_1080p.mp4"
FINAL_720 = ROOT / "runtime_evidence" / "demo_720p.mp4"
FINAL_ALIAS = ROOT / "runtime_evidence" / "demo.mp4"
FINAL_CN = ROOT / "runtime_evidence" / "赛道二_无界应用_ILearn_第16队_Demo视频.mp4"
FINAL_1080_FAST = ROOT / "runtime_evidence" / "demo_1080p_fast.mp4"
FINAL_720_FAST = ROOT / "runtime_evidence" / "demo_720p_fast.mp4"


def run(cmd: list[str], **kwargs) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def ffprobe_duration(path: Path) -> float:
    probe = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(probe)


async def synthesize_all(segments: list[dict], voice: str, rate: str, force: bool) -> None:
    import edge_tts

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for seg in segments:
        out = AUDIO_DIR / f"{seg['id']}.mp3"
        if out.exists() and out.stat().st_size > 1000 and not force:
            print(f"skip audio {out.name}")
            continue
        print(f"TTS {seg['id']} ...")
        communicate = edge_tts.Communicate(seg["narration"], voice, rate=rate)
        await communicate.save(str(out))


async def run_actions(page, base_url: str, actions: list[dict]) -> None:
    for action in actions:
        typ = action["type"]
        if typ == "goto":
            url = action["url"]
            if url.startswith("http"):
                await page.goto(url, wait_until="networkidle", timeout=60000)
            else:
                await page.goto(base_url.rstrip("/") + url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(700)
        elif typ == "wait":
            await page.wait_for_timeout(int(float(action.get("sec", 1)) * 1000))
        elif typ == "scroll":
            amount = int(action.get("amount", 300))
            await page.evaluate("(y) => window.scrollBy({top: y, behavior: 'smooth'})", amount)
            await page.wait_for_timeout(650)
        elif typ == "click":
            selector = action["selector"]
            optional = bool(action.get("optional"))
            tried = False
            for part in [s.strip() for s in selector.split(",")]:
                try:
                    await page.locator(part).first.click(timeout=6000)
                    tried = True
                    break
                except Exception:
                    continue
            if not tried and not optional:
                print(f"  warn: click miss {selector}")
            await page.wait_for_timeout(350)
        elif typ == "wait_for":
            selector = action["selector"]
            timeout_ms = int(float(action.get("sec", 15)) * 1000)
            try:
                await page.wait_for_selector(selector, timeout=timeout_ms)
                await page.wait_for_timeout(600)
            except Exception:
                print(f"  warn: wait_for miss {selector}")
        elif typ == "hold_to_audio":
            continue
        else:
            print(f"  warn: unknown action {typ}")


def _frame_looks_blank(png: Path) -> bool:
    """Heuristic: tiny PNG => blank/white solid capture (real UI screenshots are >>50KB)."""
    return (not png.exists()) or png.stat().st_size < 25000


def trim_leading_blank(vid: Path, max_keep_blank: float = 0.8, scan_sec: float = 5.0) -> float:
    """Trim leading white/blank frames; keep at most max_keep_blank seconds of blank."""
    dur = ffprobe_duration(vid)
    if dur < 1.0:
        return 0.0
    probe_dir = vid.parent / f"{vid.stem}_blankscan"
    if probe_dir.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)
    probe_dir.mkdir(parents=True, exist_ok=True)
    first_content = None
    t = 0.0
    while t < min(scan_sec, dur - 0.2):
        png = probe_dir / f"t{int(t * 100):04d}.png"
        run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{t:.2f}",
                "-i",
                str(vid),
                "-frames:v",
                "1",
                "-update",
                "1",
                str(png),
            ]
        )
        if not _frame_looks_blank(png):
            first_content = t
            break
        t += 0.25
    shutil.rmtree(probe_dir, ignore_errors=True)
    if first_content is None or first_content <= max_keep_blank:
        return 0.0
    cut = first_content - max_keep_blank
    trimmed = vid.with_name(vid.stem + "_noblank.mp4")
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{cut:.3f}",
            "-i",
            str(vid),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-an",
            "-movflags",
            "+faststart",
            str(trimmed),
        ]
    )
    shutil.move(str(trimmed), str(vid))
    print(f"  trimmed leading blank {cut:.2f}s from {vid.name} (content@{first_content:.2f}s)")
    return cut


def trim_all_leading_blanks(cfg: dict, max_keep_blank: float = 0.8) -> None:
    for seg in cfg["segments"]:
        if seg.get("mode") != "browser":
            continue
        vid = VIDEO_DIR / f"{seg['id']}.mp4"
        if vid.exists():
            trim_leading_blank(vid, max_keep_blank=max_keep_blank)


async def _record_one(browser, seg: dict, cfg: dict, cards_uri: str) -> None:
    width = int(cfg.get("width", 1920))
    height = int(cfg.get("height", 1080))
    tail = float(cfg.get("tail_pad_sec", 0.8))
    base_url = cfg["base_url"]
    raw_webm_dir = VIDEO_DIR / f"{seg['id']}_dir"
    if raw_webm_dir.exists():
        shutil.rmtree(raw_webm_dir, ignore_errors=True)
    raw_webm_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = VIDEO_DIR / f"{seg['id']}.mp4"
    audio = AUDIO_DIR / f"{seg['id']}.mp3"
    audio_sec = ffprobe_duration(audio)
    need_sec = audio_sec + tail + 0.4

    print(f"\n== Record {seg['id']} (~{need_sec:.1f}s, audio {audio_sec:.1f}s) ==")
    context = await browser.new_context(
        viewport={"width": width, "height": height},
        record_video_dir=str(raw_webm_dir),
        record_video_size={"width": width, "height": height},
        device_scale_factor=1,
    )
    page = await context.new_page()
    t0 = time.time()
    try:
        if seg.get("mode") == "card":
            q = seg.get("card_query") or "k=closing"
            await page.goto(f"{cards_uri}?{q}", wait_until="load", timeout=30000)
            await page.wait_for_timeout(800)
        else:
            await page.goto(base_url.rstrip("/") + "/", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(500)
        await run_actions(page, base_url, seg.get("actions") or [])
        # Ensure student/teacher shell painted (avoid pure-white captures).
        try:
            await page.wait_for_selector("body", timeout=5000)
            await page.wait_for_timeout(400)
        except Exception:
            pass
        elapsed = time.time() - t0
        remain = need_sec - elapsed
        if remain > 0:
            steps = max(1, int(remain / 2.2))
            for _ in range(steps):
                await page.evaluate("() => window.scrollBy({top: 80, behavior: 'smooth'})")
                await page.wait_for_timeout(int((remain / steps) * 1000))
    finally:
        await context.close()

    webms = list(raw_webm_dir.glob("*.webm"))
    if not webms:
        raise RuntimeError(f"No webm for {seg['id']}")
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(webms[0]),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]
    )
    shutil.rmtree(raw_webm_dir, ignore_errors=True)
    probe_png = VIDEO_DIR / f"{seg['id']}_probe.png"
    vdur = ffprobe_duration(out_mp4)
    # Sample mid-clip; short cards may be <6s so clamp to video length.
    sample_at = max(1.0, min(vdur * 0.45, max(vdur - 0.4, 1.0)))
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{sample_at:.2f}",
            "-i",
            str(out_mp4),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(probe_png),
        ]
    )
    if _frame_looks_blank(probe_png):
        raise RuntimeError(f"Blank/white capture detected for {seg['id']} @{sample_at:.1f}s")
    probe_png.unlink(missing_ok=True)


async def record_segments(cfg: dict, only: set[str] | None = None) -> None:
    from playwright.async_api import async_playwright

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    cards_uri = CARDS.resolve().as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for seg in cfg["segments"]:
            if only and seg["id"] not in only:
                continue
            last_err: Exception | None = None
            for attempt in range(1, 4):
                try:
                    await _record_one(browser, seg, cfg, cards_uri)
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    print(f"  retry {attempt}/3 for {seg['id']}: {e}")
                    await asyncio.sleep(1.2)
            if last_err:
                raise last_err
        await browser.close()


def mux_segments(cfg: dict) -> list[Path]:
    MUX_DIR.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    tail = float(cfg.get("tail_pad_sec", 0.8))
    for seg in cfg["segments"]:
        vid = VIDEO_DIR / f"{seg['id']}.mp4"
        aud = AUDIO_DIR / f"{seg['id']}.mp3"
        out = MUX_DIR / f"{seg['id']}.mp4"
        vdur = ffprobe_duration(vid)
        adur = ffprobe_duration(aud)
        # Keep short post-narration silence on the clip itself.
        final_dur = min(max(adur + tail, adur + 0.35), max(vdur, adur + 0.35))
        padded = MUX_DIR / f"{seg['id']}_audio_pad.m4a"
        pad_sec = max(0.0, final_dur - adur)
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(aud),
                "-af",
                f"apad=pad_dur={pad_sec:.3f},aresample=48000",
                "-t",
                f"{final_dur:.3f}",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-b:a",
                "192k",
                str(padded),
            ]
        )
        # Always re-encode A/V together at 48kHz so concat timestamps stay aligned.
        vf = "null"
        if vdur + 0.05 < final_dur:
            vpad = final_dur - vdur
            vf = f"tpad=stop_mode=clone:stop_duration={vpad:.3f}"
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(vid),
                "-i",
                str(padded),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "30",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-b:a",
                "192k",
                "-t",
                f"{final_dur:.3f}",
                "-movflags",
                "+faststart",
                str(out),
            ]
        )
        outs.append(out)
        print(f"muxed {out.name} v={vdur:.1f}s a={adur:.1f}s -> {final_dur:.1f}s")
    return outs


def make_silence(path: Path, sec: float) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#06101f:s=1920x1080:r=30",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=mono",
            "-t",
            f"{sec:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(path),
        ]
    )


def concat_final(parts: list[Path], gap_sec: float) -> None:
    lst = WORK / "concat.txt"
    gap = WORK / "gap_silence.mp4"
    if gap_sec > 0.05:
        make_silence(gap, gap_sec)
    lines: list[str] = []
    for i, p in enumerate(parts):
        path = p.resolve().as_posix().replace("'", r"\'")
        lines.append(f"file '{path}'")
        if gap_sec > 0.05 and i < len(parts) - 1:
            gpath = gap.resolve().as_posix().replace("'", r"\'")
            lines.append(f"file '{gpath}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    # Re-encode on concat for clean A/V timestamps after silence inserts.
    tmp = WORK / "final_tmp.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-vf",
            "fps=30,format=yuv420p",
            "-af",
            "aresample=48000:async=1:first_pts=0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    # Guard against A/V drift: trim to the shorter stream.
    vdur = None
    adur = None
    try:
        meta = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,duration",
                "-of",
                "json",
                str(tmp),
            ],
            text=True,
        )
        import json as _json

        for s in _json.loads(meta)["streams"]:
            if s.get("codec_type") == "video":
                vdur = float(s["duration"])
            elif s.get("codec_type") == "audio":
                adur = float(s["duration"])
    except Exception:
        pass
    if vdur and adur and abs(vdur - adur) > 1.0:
        shortest = min(vdur, adur)
        print(f"WARN A/V mismatch v={vdur:.1f} a={adur:.1f}, trim to {shortest:.1f}s")
        trimmed = WORK / "final_trimmed.mp4"
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(tmp),
                "-t",
                f"{shortest:.3f}",
                "-c",
                "copy",
                str(trimmed),
            ]
        )
        tmp = trimmed

    FINAL_1080.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tmp, FINAL_1080)
    shutil.copyfile(tmp, FINAL_CN)
    # 720p companion
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(tmp),
            "-vf",
            "scale=1280:720",
            "-c:v",
            "libx264",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(FINAL_720),
        ]
    )
    shutil.copyfile(FINAL_720, FINAL_ALIAS)
    dur = ffprobe_duration(FINAL_1080)
    size_mb = FINAL_1080.stat().st_size / (1024 * 1024)
    print(f"\nFINAL 1080p: {FINAL_1080}")
    print(f"FINAL 720p:  {FINAL_720}")
    print(f"12min archive kept: demo_*_12min.mp4")
    print(f"duration={dur:.1f}s size1080={size_mb:.1f}MB")


def speed_change(src: Path, dst_1080: Path, dst_720: Path, factor: float) -> None:
    """Speed up A/V together. factor>1 means faster / shorter."""
    # atempo accepts 0.5..2.0; chain if needed
    tempos: list[float] = []
    rem = factor
    while rem > 2.0 + 1e-6:
        tempos.append(2.0)
        rem /= 2.0
    while rem < 0.5 - 1e-6:
        tempos.append(0.5)
        rem /= 0.5
    tempos.append(rem)
    af = ",".join(f"atempo={t:.6f}" for t in tempos)
    tmp = WORK / "speed_tmp.mp4"
    WORK.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-filter_complex",
            f"[0:v]setpts=PTS/{factor}[v];[0:a]{af}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    shutil.copyfile(tmp, dst_1080)
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(tmp),
            "-vf",
            "scale=1280:720",
            "-c:v",
            "libx264",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(dst_720),
        ]
    )
    print(f"speed x{factor:.3f} -> {ffprobe_duration(dst_1080):.1f}s  {dst_1080}")


def main() -> int:
    cfg = json.loads(SEG_JSON.read_text(encoding="utf-8"))
    WORK.mkdir(parents=True, exist_ok=True)
    voice = cfg.get("voice") or "zh-CN-XiaoxiaoNeural"
    rate = cfg.get("rate") or "-8%"
    gap = float(cfg.get("inter_clip_silence_sec", 0.7))
    force_tts = "--force-tts" in sys.argv
    skip_record = "--mux-only" in sys.argv
    speed_only = "--speed-only" in sys.argv
    only: set[str] | None = None
    speed = 0.0
    for i, arg in enumerate(sys.argv):
        if arg == "--only" and i + 1 < len(sys.argv):
            only = {x.strip() for x in sys.argv[i + 1].split(",") if x.strip()}
        if arg == "--speed" and i + 1 < len(sys.argv):
            speed = float(sys.argv[i + 1])

    if speed_only:
        src = FINAL_1080 if FINAL_1080.exists() else ROOT / "runtime_evidence" / "demo_1080p_12min.mp4"
        if speed <= 0:
            # default: aim ~8.0 min from current duration
            dur = ffprobe_duration(src)
            speed = max(1.01, dur / 480.0)
            print(f"auto speed factor {speed:.3f} ({dur:.1f}s -> ~480s)")
        speed_change(src, FINAL_1080_FAST, FINAL_720_FAST, speed)
        shutil.copyfile(FINAL_1080_FAST, FINAL_1080)
        shutil.copyfile(FINAL_720_FAST, FINAL_720)
        shutil.copyfile(FINAL_720_FAST, FINAL_ALIAS)
        shutil.copyfile(FINAL_1080_FAST, FINAL_CN)
        return 0

    if not skip_record:
        if only is None:
            print("=== 1/3 edge-tts ===")
            asyncio.run(synthesize_all(cfg["segments"], voice, rate, force_tts or True))
        else:
            print("=== skip full TTS; reusing audio (only re-record) ===")
            # still ensure missing audio exists for selected ids
            need = [s for s in cfg["segments"] if s["id"] in only]
            asyncio.run(synthesize_all(need, voice, rate, force_tts))

        print("=== 2/3 record segments ===")
        asyncio.run(record_segments(cfg, only=only))
        print("=== 2b/3 trim leading blank (<=0.8s keep) ===")
        trim_all_leading_blanks(cfg, max_keep_blank=0.8)
    else:
        print("=== mux-only: reuse existing raw video + audio ===")
        if "--trim-blank" in sys.argv:
            print("=== trim leading blank ===")
            trim_all_leading_blanks(cfg, max_keep_blank=0.8)

    print("=== 3/3 mux + concat ===")
    parts = mux_segments(cfg)
    concat_final(parts, gap)

    if speed > 0:
        print(f"=== speed x{speed:.3f} ===")
        speed_change(FINAL_1080, FINAL_1080_FAST, FINAL_720_FAST, speed)
        shutil.copyfile(FINAL_1080_FAST, FINAL_1080)
        shutil.copyfile(FINAL_720_FAST, FINAL_720)
        shutil.copyfile(FINAL_720_FAST, FINAL_ALIAS)
        shutil.copyfile(FINAL_1080_FAST, FINAL_CN)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print("command failed:", e, file=sys.stderr)
        raise SystemExit(1)
