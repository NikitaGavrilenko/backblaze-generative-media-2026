from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "submission-assets" / "video"
FRAME_DIR = VIDEO_DIR / "frames"
CAPTIONED_DIR = VIDEO_DIR / "captioned"
SEGMENT_DIR = VIDEO_DIR / "segments"
OUTPUT = VIDEO_DIR / "proofstudio-demo.mp4"
SRT_OUTPUT = VIDEO_DIR / "proofstudio-demo-en.srt"

WIDTH = 1280
HEIGHT = 720
FPS = 30

REGULAR_FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
BOLD_FONT = Path(r"C:\Windows\Fonts\segoeuib.ttf")


SCENES = [
    {
        "name": "00-title",
        "duration": 7,
        "caption": "ProofStudio creates durable, verifiable generative media.",
        "kind": "title",
    },
    {
        "name": "01-home",
        "duration": 11,
        "caption": "A single application connects structured creative direction, generation, storage, and verification.",
        "source": "01-home.png",
    },
    {
        "name": "02-brief",
        "duration": 12,
        "caption": "The campaign brief captures audience, message, tone, constraints, and aspect ratio as structured input.",
        "source": "02-brief.png",
    },
    {
        "name": "03-history",
        "duration": 11,
        "caption": "Live Mode restores durable run history from private Backblaze B2 after deployment restarts.",
        "source": "03-history.png",
    },
    {
        "name": "04-assets",
        "duration": 15,
        "caption": "This public run generated two landscape variants with Cloudflare Workers AI and stored both originals in B2.",
        "source": "04-assets.png",
    },
    {
        "name": "05-provenance",
        "duration": 16,
        "caption": "Genblaze records the exact model, prompt, parameters, provider request IDs, asset hashes, and canonical manifest hash.",
        "source": "05-provenance.png",
    },
    {
        "name": "08-verified",
        "duration": 13,
        "caption": "Verification downloads the stored manifest and assets, then recomputes every SHA-256 hash.",
        "source": "08-verified.png",
    },
    {
        "name": "99-end",
        "duration": 9,
        "caption": "Two images. One canonical manifest. Verifiable after restart.",
        "kind": "end",
    },
]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, selected_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=selected_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def caption_overlay(image: Image.Image, caption: str) -> Image.Image:
    canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    panel_top = HEIGHT - 126
    draw.rectangle((0, panel_top, WIDTH, HEIGHT), fill=(12, 12, 12, 226))
    draw.rectangle((0, panel_top, 12, HEIGHT), fill=(238, 101, 67, 255))
    caption_font = font(BOLD_FONT, 30)
    lines = wrap_text(draw, caption, caption_font, WIDTH - 150)
    line_height = 39
    total_height = len(lines) * line_height
    y = panel_top + (126 - total_height) // 2 - 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=caption_font)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=caption_font, fill=(255, 255, 255, 255))
        y += line_height
    return Image.alpha_composite(canvas, overlay).convert("RGB")


def centered_lines(draw: ImageDraw.ImageDraw, lines: list[tuple[str, ImageFont.FreeTypeFont, tuple[int, int, int]]], start_y: int, gap: int) -> None:
    y = start_y
    for text, selected_font, color in lines:
        bbox = draw.textbbox((0, 0), text, font=selected_font)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), text, font=selected_font, fill=color)
        y += (bbox[3] - bbox[1]) + gap


def title_card(caption: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f3f0e7")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 18, HEIGHT), fill="#ee6543")
    draw.text((76, 62), "GENBLAZE · BACKBLAZE B2", font=font(BOLD_FONT, 20), fill="#ee6543")
    centered_lines(
        draw,
        [
            ("ProofStudio", font(BOLD_FONT, 78), (20, 20, 20)),
            ("Durable, verifiable generative media", font(REGULAR_FONT, 34), (52, 52, 52)),
            ("Cloudflare Workers AI  →  Genblaze  →  Backblaze B2", font(BOLD_FONT, 26), (20, 20, 20)),
        ],
        190,
        34,
    )
    draw.rounded_rectangle((282, 468, 998, 532), radius=18, fill="#151515")
    url = "proofstudio-h3ds.onrender.com"
    url_font = font(BOLD_FONT, 26)
    bbox = draw.textbbox((0, 0), url, font=url_font)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, 483), url, font=url_font, fill="white")
    return caption_overlay(image, caption)


def end_card(caption: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#161616")
    draw = ImageDraw.Draw(image)
    draw.text((76, 64), "PROOFSTUDIO", font=font(BOLD_FONT, 20), fill="#ee6543")
    centered_lines(
        draw,
        [
            ("Two generated assets.", font(BOLD_FONT, 56), (255, 255, 255)),
            ("One canonical manifest.", font(BOLD_FONT, 56), (255, 255, 255)),
            ("Verified after deployment restart.", font(REGULAR_FONT, 32), (214, 211, 201)),
        ],
        168,
        24,
    )
    draw.rounded_rectangle((286, 480, 994, 544), radius=18, outline="#ee6543", width=3)
    url = "proofstudio-h3ds.onrender.com"
    url_font = font(BOLD_FONT, 26)
    bbox = draw.textbbox((0, 0), url, font=url_font)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, 495), url, font=url_font, fill="white")
    return caption_overlay(image, caption)


def timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def locate_ffmpeg() -> Path:
    executable = shutil.which("ffmpeg")
    if executable:
        return Path(executable)
    packages = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    matches = sorted(packages.glob("Gyan.FFmpeg.Essentials_*/*/bin/ffmpeg.exe"))
    if not matches:
        matches = sorted(packages.rglob("ffmpeg.exe"))
    if not matches:
        raise FileNotFoundError("FFmpeg was not found after installation.")
    return matches[-1]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    CAPTIONED_DIR.mkdir(parents=True, exist_ok=True)
    SEGMENT_DIR.mkdir(parents=True, exist_ok=True)

    srt_blocks: list[str] = []
    elapsed = 0.0
    for index, scene in enumerate(SCENES, start=1):
        if scene.get("kind") == "title":
            image = title_card(scene["caption"])
        elif scene.get("kind") == "end":
            image = end_card(scene["caption"])
        else:
            source = Image.open(FRAME_DIR / scene["source"])
            image = caption_overlay(source.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS), scene["caption"])
        image.save(CAPTIONED_DIR / f"{scene['name']}.png", quality=95)

        start = elapsed
        elapsed += scene["duration"]
        srt_blocks.append(
            f"{index}\n{timestamp(start)} --> {timestamp(elapsed)}\n{scene['caption']}\n"
        )
    SRT_OUTPUT.write_text("\n".join(srt_blocks), encoding="utf-8")

    ffmpeg = locate_ffmpeg()
    segment_paths: list[Path] = []
    for scene in SCENES:
        duration = scene["duration"]
        frames = duration * FPS
        fade_out = duration - 0.45
        source = CAPTIONED_DIR / f"{scene['name']}.png"
        target = SEGMENT_DIR / f"{scene['name']}.mp4"
        filter_graph = (
            f"scale={WIDTH}:{HEIGHT},"
            f"zoompan=z='min(zoom+0.00010,1.025)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
            f"fade=t=in:st=0:d=0.45,fade=t=out:st={fade_out}:d=0.45,format=yuv420p"
        )
        run(
            [
                str(ffmpeg),
                "-y",
                "-loop",
                "1",
                "-i",
                str(source),
                "-t",
                str(duration),
                "-vf",
                filter_graph,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(target),
            ]
        )
        segment_paths.append(target)

    concat_file = SEGMENT_DIR / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    run(
        [
            str(ffmpeg),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ]
    )
    print(f"Created {OUTPUT} ({elapsed:.0f} seconds)")


if __name__ == "__main__":
    main()
