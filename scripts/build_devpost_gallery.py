from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "submission-assets" / "video" / "frames"
OUTPUT_DIR = ROOT / "submission-assets" / "devpost-gallery"
WIDTH = 1200
HEIGHT = 800
HEADER_HEIGHT = 125
REGULAR_FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
BOLD_FONT = Path(r"C:\Windows\Fonts\segoeuib.ttf")


SLIDES = [
    (
        "01-structured-brief.png",
        "02-brief.png",
        "01 / STRUCTURED INPUT",
        "Turn campaign direction into a reproducible generation brief",
    ),
    (
        "02-verified-output.png",
        "04-assets.png",
        "02 / VERIFIED OUTPUT",
        "Two live Cloudflare Workers AI variants stored durably in Backblaze B2",
    ),
    (
        "03-provenance.png",
        "05-provenance.png",
        "03 / PROVENANCE",
        "Exact model, prompt, parameters, provider IDs, and canonical manifest hash",
    ),
    (
        "04-durable-history.png",
        "03-history.png",
        "04 / DURABLE HISTORY",
        "Run metadata, assets, and manifests restored after deployment restart",
    ),
]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def build_slide(source_name: str, label: str, subtitle: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f3f0e7")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 14, HEIGHT), fill="#ee6543")
    draw.text((52, 28), label, font=font(BOLD_FONT, 22), fill="#ee6543")
    draw.text((52, 65), subtitle, font=font(REGULAR_FONT, 24), fill="#202020")

    screenshot = Image.open(SOURCE_DIR / source_name).convert("RGB")
    screenshot = screenshot.resize((WIDTH, HEIGHT - HEADER_HEIGHT), Image.Resampling.LANCZOS)
    image.paste(screenshot, (0, HEADER_HEIGHT))
    draw.rectangle((0, HEADER_HEIGHT, 14, HEIGHT), fill="#ee6543")
    return image


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for output_name, source_name, label, subtitle in SLIDES:
        output = OUTPUT_DIR / output_name
        build_slide(source_name, label, subtitle).save(output, optimize=True)
        print(f"Created {output}")


if __name__ == "__main__":
    main()
