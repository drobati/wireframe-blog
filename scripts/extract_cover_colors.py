#!/usr/bin/env python3
"""Extract dominant colors from book cover images and add to books.json."""

import colorsys
import json
import urllib.request
from collections import Counter
from io import BytesIO
from pathlib import Path
from PIL import Image


def color_score(rgb):
    """Score a color for book spine use — prefer saturated, medium-brightness."""
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # Strongly prefer saturated colors
    sat_score = s
    # Prefer medium brightness (not washed out, not too dark)
    bright_score = 1.0 - abs(v - 0.45) * 2
    return sat_score * 0.7 + max(bright_score, 0) * 0.3


def get_dominant_color(image_url):
    """Fetch image and return dominant vibrant color as hex string."""
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()

    img = Image.open(BytesIO(data)).convert("RGB")
    img = img.resize((80, 80))

    pixels = list(img.getdata())

    # Bucket pixels into coarse bins (8 bins per channel → 512 possible colors)
    def bucket(pixel):
        return tuple(c // 32 * 32 + 16 for c in pixel)

    bucketed = [bucket(p) for p in pixels]

    # Filter out near-black and near-white
    filtered = [p for p in bucketed if 80 < sum(p) < 660]
    if not filtered:
        filtered = bucketed

    # Find top 8 most common colors
    counter = Counter(filtered)
    top_colors = [color for color, _ in counter.most_common(8)]

    # Pick the one with the best "book spine" score
    best = max(top_colors, key=color_score)
    return "#{:02x}{:02x}{:02x}".format(*best)


def main():
    data_path = Path(__file__).resolve().parent.parent / "_data" / "books.json"
    with open(data_path, "r") as f:
        books = json.load(f)

    updated = 0
    for i, book in enumerate(books):
        url = book.get("image_url")
        title = book.get("title", "?")

        if not url:
            print(f"[{i + 1}/{len(books)}] {title} — no image URL, skipped")
            continue

        print(f"[{i + 1}/{len(books)}] {title}...", end=" ", flush=True)
        try:
            color = get_dominant_color(url)
            book["cover_color"] = color
            updated += 1
            print(f"-> {color}")
        except Exception as e:
            print(f"-> ERROR: {e}")

    with open(data_path, "w") as f:
        json.dump(books, f, indent=2)
        f.write("\n")

    print(f"\nDone! Updated {updated}/{len(books)} books.")


if __name__ == "__main__":
    main()
