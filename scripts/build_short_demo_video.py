#!/usr/bin/env python3
"""Build 1min / 2min GOAI demo videos from doc/video_1-2_min.txt.

Usage (repo root, FE+BE up for 2min browser segments):
  python scripts/build_short_demo_video.py --variant 1min
  python scripts/build_short_demo_video.py --variant 2min
  python scripts/build_short_demo_video.py --variant both
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "doc" / "submit" / "demo_cards.html"
EVIDENCE = ROOT / "runtime_evidence"

VARIANTS = {
    "1min": {
        "json": ROOT / "doc" / "submit" / "goai_video_segments_1min.json",
        "work": EVIDENCE / "goai_video_build_1min",
        "out_1080": EVIDENCE / "ILearn_1min_Demo.mp4",
        "out_720": EVIDENCE / "ILearn_1min_Demo_720p.mp4",
        "target_sec": 60,
    },
    "2min": {
        "json": ROOT / "doc" / "submit" / "goai_video_segments_2min.json",
        "work": EVIDENCE / "goai_video_build_2min",
        "out_1080": EVIDENCE / "ILearn_2min_Demo.mp4",
        "out_720": EVIDENCE / "ILearn_2min_Demo_720p.mp4",
        "target_sec": 120,
    },
}


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    return float(
        subprocess.check_output(
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
    )


def seg_duration(seg: dict, audio_sec: float) -> float:
    fixed = float(seg.get("duration_sec") or 0)
    if fixed > 0 and audio_sec > 0.1:
        return max(fixed, audio_sec)
    if fixed > 0:
        return fixed
    return audio_sec


async def synthesize_segments(segments: list[dict], audio_dir: Path, voice: str, rate: str) -> None:
    import edge_tts

    audio_dir.mkdir(parents=True, exist_ok=True)
    for seg in segments:
        out = audio_dir / f"{seg['id']}.mp3"
        text = (seg.get("narration") or "").strip()
        if not text:
            dur = float(seg.get("duration_sec") or 5)
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=mono",
                    "-t",
                    f"{dur:.3f}",
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "9",
                    str(out),
                ]
            )
            print(f"silent audio {seg['id']} {dur:.1f}s")
            continue
        print(f"TTS {seg['id']} ...")
        await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


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


def _frame_looks_blank(png: Path) -> bool:
    return (not png.exists()) or png.stat().st_size < 25000


async def record_segments(cfg: dict, paths: dict) -> None:
    from playwright.async_api import async_playwright

    video_dir = paths["video"]
    audio_dir = paths["audio"]
    video_dir.mkdir(parents=True, exist_ok=True)
    cards_uri = CARDS.resolve().as_uri()
    width = int(cfg.get("width", 1920))
    height = int(cfg.get("height", 1080))
    tail = float(cfg.get("tail_pad_sec", 0.3))
    base_url = cfg["base_url"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for seg in cfg["segments"]:
            raw_dir = video_dir / f"{seg['id']}_dir"
            if raw_dir.exists():
                shutil.rmtree(raw_dir, ignore_errors=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
            out_mp4 = video_dir / f"{seg['id']}.mp4"
            audio = audio_dir / f"{seg['id']}.mp3"
            audio_sec = ffprobe_duration(audio)
            need_sec = seg_duration(seg, audio_sec) + tail + 0.25

            print(f"\n== Record {seg['id']} (~{need_sec:.1f}s) ==")
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                record_video_dir=str(raw_dir),
                record_video_size={"width": width, "height": height},
            )
            page = await context.new_page()
            try:
                if seg.get("mode") == "card":
                    q = seg.get("card_query") or "k=closing"
                    await page.goto(f"{cards_uri}?{q}", wait_until="load", timeout=30000)
                    await page.wait_for_timeout(600)
                else:
                    await page.goto(base_url.rstrip("/") + "/", wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(400)
                await run_actions(page, base_url, seg.get("actions") or [])
                elapsed_ms = int((need_sec - 0.5) * 1000)
                if elapsed_ms > 0:
                    await page.wait_for_timeout(min(elapsed_ms, 15000))
            finally:
                await context.close()

            webms = list(raw_dir.glob("*.webm"))
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
            shutil.rmtree(raw_dir, ignore_errors=True)

            probe = video_dir / f"{seg['id']}_probe.png"
            sample = max(1.0, min(need_sec * 0.45, ffprobe_duration(out_mp4) - 0.5))
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{sample:.2f}",
                    "-i",
                    str(out_mp4),
                    "-frames:v",
                    "1",
                    "-update",
                    "1",
                    str(probe),
                ]
            )
            if _frame_looks_blank(probe):
                raise RuntimeError(f"Blank capture for {seg['id']} @{sample:.1f}s")
            probe.unlink(missing_ok=True)
        await browser.close()


def mux_segments(cfg: dict, paths: dict) -> list[Path]:
    mux_dir = paths["mux"]
    video_dir = paths["video"]
    audio_dir = paths["audio"]
    mux_dir.mkdir(parents=True, exist_ok=True)
    tail = float(cfg.get("tail_pad_sec", 0.3))
    outs: list[Path] = []

    for seg in cfg["segments"]:
        vid = video_dir / f"{seg['id']}.mp4"
        aud = audio_dir / f"{seg['id']}.mp3"
        out = mux_dir / f"{seg['id']}.mp4"
        vdur = ffprobe_duration(vid)
        adur = ffprobe_duration(aud)
        target = float(seg.get("duration_sec") or 0)
        if target > 0 and adur > 0.1:
            final_dur = max(target, adur + tail)
        elif adur > 0.1:
            final_dur = max(adur + tail, adur + 0.25)
        else:
            final_dur = target if target > 0 else max(vdur, 1.0)
        final_dur = max(final_dur, min(vdur, adur + 0.2) if adur > 0.1 else vdur)

        padded = mux_dir / f"{seg['id']}_pad.m4a"
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
                "128k",
                str(padded),
            ]
        )
        vf = "null"
        if vdur + 0.05 < final_dur:
            vf = f"tpad=stop_mode=clone:stop_duration={final_dur - vdur:.3f}"
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
                "128k",
                "-t",
                f"{final_dur:.3f}",
                "-movflags",
                "+faststart",
                str(out),
            ]
        )
        outs.append(out)
        print(f"muxed {out.name} -> {final_dur:.1f}s")
    return outs


def make_gap(path: Path, sec: float) -> None:
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
            "-ar",
            "48000",
            "-shortest",
            str(path),
        ]
    )


def concat_parts(parts: list[Path], gap_sec: float, work: Path, out_1080: Path, out_720: Path, crf: int) -> float:
    gap_file = work / "gap.mp4"
    lst = work / "concat.txt"
    if gap_sec > 0.05:
        make_gap(gap_file, gap_sec)
    lines: list[str] = []
    for i, p in enumerate(parts):
        lines.append(f"file '{p.resolve().as_posix().replace(chr(39), chr(92)+chr(39))}'")
        if gap_sec > 0.05 and i < len(parts) - 1:
            lines.append(f"file '{gap_file.resolve().as_posix().replace(chr(39), chr(92)+chr(39))}'")
    lst.write_text("\n".join(lines), encoding="utf-8")

    tmp = work / "final.mp4"
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
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    out_1080.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tmp, out_1080)
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
            str(crf + 2),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(out_720),
        ]
    )
    return ffprobe_duration(out_1080)


def maybe_speed_to_target(src: Path, dst: Path, target_sec: float, allow_slowdown: bool = True) -> None:
    dur = ffprobe_duration(src)
    if abs(dur - target_sec) <= 3:
        return
    factor = dur / target_sec
    if factor < 1.0 and not allow_slowdown:
        print(f"keep natural {dur:.1f}s (target {target_sec}s, no slowdown)")
        return
    factor = max(0.85, min(factor, 1.35))
    tempos: list[float] = []
    rem = factor
    while rem > 2.0:
        tempos.append(2.0)
        rem /= 2.0
    while rem < 0.5:
        tempos.append(0.5)
        rem /= 0.5
    tempos.append(rem)
    af = ",".join(f"atempo={t:.6f}" for t in tempos)
    tmp = src.parent / f"{src.stem}_speed.mp4"
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
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    shutil.copyfile(tmp, dst)
    print(f"speed adjust x{factor:.3f}: {dur:.1f}s -> {ffprobe_duration(dst):.1f}s")


async def build_variant(name: str, mux_only: bool = False) -> None:
    meta = VARIANTS[name]
    cfg = json.loads(meta["json"].read_text(encoding="utf-8"))
    work = meta["work"]
    paths = {
        "audio": work / "audio",
        "video": work / "video_raw",
        "mux": work / "muxed",
    }
    work.mkdir(parents=True, exist_ok=True)

    voice = cfg.get("voice") or "zh-CN-XiaoxiaoNeural"
    rate = cfg.get("rate") or "+0%"
    gap = float(cfg.get("inter_clip_silence_sec", 0.35))
    crf = 26 if name == "1min" else 24

    print(f"\n========== BUILD {name} ==========")
    print("=== TTS / silent audio ===")
    await synthesize_segments(cfg["segments"], paths["audio"], voice, rate)

    if not mux_only:
        print("=== record ===")
        await record_segments(cfg, paths)
    else:
        print("=== skip record (mux-only) ===")

    print("=== mux + concat ===")
    parts = mux_segments(cfg, paths)
    dur = concat_parts(parts, gap, work, meta["out_1080"], meta["out_720"], crf)
    maybe_speed_to_target(meta["out_1080"], meta["out_1080"], float(meta["target_sec"]), allow_slowdown=(name == "1min"))
    # Re-encode 720p from final 1080p (speed step only touches 1080p).
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(meta["out_1080"]),
            "-vf",
            "scale=1280:720",
            "-c:v",
            "libx264",
            "-crf",
            str(crf + 2),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(meta["out_720"]),
        ]
    )

    dur = ffprobe_duration(meta["out_1080"])
    mb = meta["out_1080"].stat().st_size / (1024 * 1024)
    print(f"DONE {name}: {meta['out_1080']}  {dur:.1f}s  {mb:.1f}MB")


def main() -> int:
    variant = "both"
    mux_only = "--mux-only" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "--variant" and i + 1 < len(sys.argv):
            variant = sys.argv[i + 1]

    names = ["1min", "2min"] if variant == "both" else [variant]
    for n in names:
        if n not in VARIANTS:
            print(f"unknown variant: {n}", file=sys.stderr)
            return 1
        asyncio.run(build_variant(n, mux_only=mux_only))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print("command failed:", e, file=sys.stderr)
        raise SystemExit(1)
