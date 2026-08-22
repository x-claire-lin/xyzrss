from pathlib import Path
import urllib.request
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
        return response.read()


def fix_feed(data, feed_id):
    """
    Change Xiaoyuzhou's enclosure MIME type:

        audio/mp4
            ↓
        audio/x-m4a
    """

    text = data.decode("utf-8")

    def replace_enclosure(match):
        tag = match.group(0)

        return tag.replace(
            'type="audio/mp4"',
            'type="audio/x-m4a"'
        )

    fixed = re.sub(
        r"<enclosure\b[^>]*/?>",
        replace_enclosure,
        text,
        flags=re.IGNORECASE
    )

    return fixed.encode("utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    feeds_file = Path("feeds.txt")

    if not feeds_file.exists():
        raise FileNotFoundError("feeds.txt not found")

    feeds = []

    for line in feeds_file.read_text(encoding="utf-8").splitlines():

        line = line.strip()

        # Empty line
        if not line:
            continue

        # Full-line comment
        if line.startswith("#"):
            continue

        # Remove inline comment
        feed_id = line.split("#", 1)[0].strip()

        # Validate feed ID
        if not re.fullmatch(r"[A-Za-z0-9_-]+", feed_id):
            print(f"Skipping invalid feed ID: {feed_id}")
            continue

        feeds.append(feed_id)

    if not feeds:
        raise RuntimeError("No valid feed IDs found")

    for feed_id in feeds:
        try:
            original = fetch_feed(feed_id)
            fixed = fix_feed(original, feed_id)

            output_file = OUTPUT_DIR / f"{feed_id}.xml"
            output_file.write_bytes(fixed)

            print(f"Written: {output_file}")

        except Exception as e:
            print(f"ERROR processing {feed_id}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
