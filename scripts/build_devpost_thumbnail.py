from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "submission-assets" / "devpost-thumbnail.png"
WIDTH = 1200
HEIGHT = 800
REGULAR_FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
BOLD_FONT = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    selected_font: ImageFont.FreeTypeFont,
    color: str,
) -> None:
    box = draw.textbbox((0, 0), text, font=selected_font)
    x = (WIDTH - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=selected_font, fill=color)


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f3f0e7")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, 22, HEIGHT), fill="#ee6543")
    draw.text(
        (78, 68),
        "GENBLAZE · BACKBLAZE B2",
        font=font(BOLD_FONT, 22),
        fill="#ee6543",
    )

    centered_text(draw, "ProofStudio", 220, font(BOLD_FONT, 94), "#151515")
    centered_text(
        draw,
        "Durable, verifiable generative media",
        345,
        font(REGULAR_FONT, 38),
        "#3b3b3b",
    )

    draw.rounded_rectangle((190, 460, 1010, 536), radius=20, fill="#151515")
    centered_text(
        draw,
        "Cloudflare Workers AI  →  Genblaze  →  Backblaze B2",
        481,
        font(BOLD_FONT, 25),
        "#ffffff",
    )

    centered_text(
        draw,
        "GENERATE  ·  STORE  ·  VERIFY",
        650,
        font(BOLD_FONT, 22),
        "#ee6543",
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
