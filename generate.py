from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
import re


SOURCE_BASE = "https://feed.xyzfm.space/"
OUTPUT_DIR = Path("docs")


def fetch_feed(feed_id):
    url = SOURCE_BASE + feed_id

    print(f"Fetching: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (RSS updater)"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()

    return data


def fix_feed(data, feed_id):
    """
    Change Xiaoyuzhou's enclosure MIME type:

        audio/mp4
            ↓
        audio/x-m4a

    Everything else remains unchanged.
    """

    text = data.decode("utf-8")

    original_count = text.count('type="audio/mp4"')

    text = text.replace(
        'type="audio/mp4"',
        'type="audio/x-m4a"'
    )

    fixed_count = text.count('type="audio/x-m4a"')

    print(
        f"{feed_id}: "
        f"replaced {original_count} enclosure(s)"
    )

    return text.encode("utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    feeds_file = Path("feeds.txt")

    if not feeds_file.exists():
        raise FileNotFoundError("feeds.txt not found")

    feed_ids = []

    for line in feeds_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        # Feed IDs should only contain these characters.
        if not re.fullmatch(r"[A-Za-z0-9_-]+", line):
            print(f"Skipping invalid feed ID: {line}")
            continue

        feed_ids.append(line)

    if not feed_ids:
        raise RuntimeError("No feed IDs found in feeds.txt")

    for feed_id in feed_ids:
        try:
            original = fetch_feed(feed_id)

            fixed = fix_feed(
                original,
                feed_id
            )

            output_file = OUTPUT_DIR / f"{feed_id}.xml"

            output_file.write_bytes(fixed)

            print(f"Written: {output_file}")

        except Exception as e:
            print(
                f"ERROR processing {feed_id}: {e}"
            )

    print("Done.")


if __name__ == "__main__":
    main()
