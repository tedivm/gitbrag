#!/usr/bin/env python3
"""Generate Open Graph social media preview image for GitBrag.

Creates a 1200x630px image with GitHub-style dark background and centered text.
This is used for social media link previews (Twitter, LinkedIn, Slack, etc.).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def generate_og_image(output_path: str | Path) -> None:
    """Generate an Open Graph preview image for social media.

    Args:
        output_path: Path where the image should be saved
    """
    # Standard Open Graph image dimensions (optimized for all platforms)
    width = 1200
    height = 630

    # GitHub dark theme background color
    bg_color = "#24292e"

    # Create image with dark background
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # Text colors
    primary_color = "#ffffff"  # White for main text
    secondary_color = "#8b949e"  # Gray for tagline (GitHub text secondary)

    # Font sizes - much larger for better readability
    title_size = 140
    tagline_size = 52

    # Try to use fonts with multiple fallback options
    title_font = None
    tagline_font = None

    # List of font paths to try (monospace and sans-serif)
    font_paths = [
        # macOS
        ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", "monospace"),
        ("/System/Library/Fonts/Courier.dfont", "monospace"),
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "sans-serif"),
        ("/System/Library/Fonts/Helvetica.ttc", "sans-serif"),
        # Windows
        ("C:\\Windows\\Fonts\\courbd.ttf", "monospace"),
        ("C:\\Windows\\Fonts\\cour.ttf", "monospace"),
        ("C:\\Windows\\Fonts\\arialbd.ttf", "sans-serif"),
        ("C:\\Windows\\Fonts\\arial.ttf", "sans-serif"),
        # Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "monospace"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "monospace"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "sans-serif"),
        ("/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf", "monospace"),
    ]

    for font_path, font_type in font_paths:
        try:
            title_font = ImageFont.truetype(font_path, title_size)
            tagline_font = ImageFont.truetype(font_path, tagline_size)
            print(f"Using {font_type} font: {font_path}")
            break
        except OSError:
            continue

    if title_font is None:
        # Fail with a helpful error message
        error_msg = (
            "ERROR: No suitable fonts found on this system.\n"
            "The Open Graph image requires consistent, high-quality fonts.\n\n"
            "Attempted font paths:\n"
        )
        for font_path, font_type in font_paths:
            error_msg += f"  - {font_path} ({font_type})\n"
        error_msg += (
            "\nPlease install one of the following:\n"
            "  macOS: Courier New or Arial (usually pre-installed)\n"
            "  Windows: Courier New or Arial (usually pre-installed)\n"
            "  Linux: sudo apt-get install fonts-dejavu or fonts-liberation\n"
        )
        raise RuntimeError(error_msg)

    # Main title text
    title_text = "git brag"

    # Calculate title position (centered horizontally, upper-middle vertically)
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    title_x = (width - title_width) // 2
    title_y = (height - title_height) // 2 - 60  # Offset up to make room for tagline

    # Draw title
    draw.text((title_x, title_y), title_text, fill=primary_color, font=title_font)

    # Tagline text
    tagline_text = "Open Source Contribution Reports"

    # Calculate tagline position (centered horizontally, below title)
    tagline_bbox = draw.textbbox((0, 0), tagline_text, font=tagline_font)
    tagline_width = tagline_bbox[2] - tagline_bbox[0]
    tagline_x = (width - tagline_width) // 2
    tagline_y = title_y + title_height + 40  # Below title with spacing

    # Draw tagline
    draw.text((tagline_x, tagline_y), tagline_text, fill=secondary_color, font=tagline_font)

    # Save the image
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG", optimize=True)

    # Get file size
    file_size_kb = output_path.stat().st_size / 1024

    print(f"✓ Generated Open Graph image: {output_path}")
    print(f"  Size: {width}x{height}px")
    print(f"  File size: {file_size_kb:.1f} KB")


if __name__ == "__main__":
    # Generate image in the static images directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_path = project_root / "gitbrag" / "static" / "images" / "og-image.png"

    generate_og_image(output_path)
