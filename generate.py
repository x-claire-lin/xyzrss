from pathlib import Path
import argparse
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime


SOURCE_BASE = "https://feed.xyzfm.space/"
OUTPUT_DIR = Path("docs")
FEEDS_FILE = Path("feeds.txt")
INDEX_FILE = OUTPUT_DIR / "feeds.json"

USER_AGENT = "xyzrss/2.0 (+https://github.com/x-claire-lin/xyzrss)"

FEED_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def fetch_feed(feed_id):
    url = SOURCE_BASE + feed_id

    print(f"Fetching: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()

    if not data:
        raise RuntimeError("Empty response")

    return data


def local_name(tag):
    """Return XML tag name without namespace."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def find_child(element, name):
    """Find direct child by local XML name."""
    for child in element:
        if local_name(child.tag).lower() == name.lower():
            return child
    return None


def find_descendant(element, name):
    """Find first descendant by local XML name."""
    for child in element.iter():
        if local_name(child.tag).lower() == name.lower():
            return child
    return None


def get_text(element):
    if element is None:
        return ""
    return (element.text or "").strip()


def parse_metadata(data, feed_id):
    """Extract basic podcast metadata from RSS."""
    root = ET.fromstring(data)

    channel = None

    if local_name(root.tag).lower() == "rss":
        channel = find_child(root, "channel")
    elif local_name(root.tag).lower() == "channel":
        channel = root
    else:
        # Atom fallback
        channel = root

    title = ""
    image = ""
    description = ""

    if channel is not None:
        title_element = find_child(channel, "title")
        title = get_text(title_element)

        description_element = find_child(channel, "description")
        description = get_text(description_element)

        # Standard RSS image
        image_element = find_child(channel, "image")
        if image_element is not None:
            url_element = find_child(image_element, "url")
            image = get_text(url_element)

        # iTunes image
        if not image:
            for child in channel:
                if local_name(child.tag).lower() == "image":
                    href = child.attrib.get("href", "").strip()
                    if href:
                        image = href

        # Search for namespaced itunes:image
        if not image:
            for child in channel.iter():
                if local_name(child.tag).lower() == "image":
                    href = child.attrib.get("href", "").strip()
                    if href:
                        image = href

    if not title:
        title = feed_id

    return {
        "id": feed_id,
        "title": title,
        "image": image,
        "description": description,
        "source": SOURCE_BASE + feed_id,
        "rss": f"{feed_id}.xml",
    }


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

        return re.sub(
            r'type\s*=\s*["\']audio/mp4["\']',
            'type="audio/x-m4a"',
            tag,
            flags=re.IGNORECASE,
        )

    fixed = re.sub(
        r"<enclosure\b[^>]*/?>",
        replace_enclosure,
        text,
        flags=re.IGNORECASE,
    )

    return fixed.encode("utf-8")


def read_feeds():
    """
    Read feeds.txt.

    Format:
        feed_id # Podcast Name
    """

    if not FEEDS_FILE.exists():
        raise FileNotFoundError("feeds.txt not found")

    feeds = []

    for line in FEEDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        parts = line.split("#", 1)
        feed_id = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ""

        if not FEED_ID_PATTERN.fullmatch(feed_id):
            print(f"Skipping invalid feed ID: {feed_id}")
            continue

        feeds.append({
            "id": feed_id,
            "title": title,
        })

    return feeds


def write_feed_metadata(feed_metadata):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    feed_metadata = sorted(
        feed_metadata,
        key=lambda item: item["title"].lower()
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feeds": feed_metadata,
    }

    INDEX_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Written: {INDEX_FILE}")


def load_existing_metadata():
    if not INDEX_FILE.exists():
        return []

    try:
        data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        return data.get("feeds", [])
    except Exception:
        return []


def update_single(feed_id):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    original = fetch_feed(feed_id)
    fixed = fix_feed(original, feed_id)

    output_file = OUTPUT_DIR / f"{feed_id}.xml"
    output_file.write_bytes(fixed)

    metadata = parse_metadata(original, feed_id)

    existing = load_existing_metadata()

    replaced = False
    for index, item in enumerate(existing):
        if item.get("id") == feed_id:
            existing[index] = metadata
            replaced = True
            break

    if not replaced:
        existing.append(metadata)

    write_feed_metadata(existing)

    print(f"Written: {output_file}")


def update_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    feeds = read_feeds()

    if not feeds:
        raise RuntimeError("No valid feed IDs found")

    metadata = []

    for feed in feeds:
        feed_id = feed["id"]

        try:
            original = fetch_feed(feed_id)
            fixed = fix_feed(original, feed_id)

            output_file = OUTPUT_DIR / f"{feed_id}.xml"
            output_file.write_bytes(fixed)

            item = parse_metadata(original, feed_id)

            # Prefer the manually supplied name in feeds.txt.
            if feed["title"]:
                item["title"] = feed["title"]

            metadata.append(item)

            print(f"Written: {output_file}")

        except Exception as error:
            print(f"ERROR processing {feed_id}: {error}")

            # Preserve existing metadata if one feed temporarily fails.
            existing = load_existing_metadata()

            for item in existing:
                if item.get("id") == feed_id:
                    metadata.append(item)
                    break

    write_feed_metadata(metadata)

    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Anytime-compatible Xiaoyuzhou RSS feeds."
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--all",
        action="store_true",
        help="Update all feeds listed in feeds.txt.",
    )

    group.add_argument(
        "--feed",
        help="Update a single feed by ID.",
    )

    args = parser.parse_args()

    if args.all:
        update_all()
    elif args.feed:
        if not FEED_ID_PATTERN.fullmatch(args.feed):
            raise ValueError(f"Invalid feed ID: {args.feed}")

        update_single(args.feed)


if __name__ == "__main__":
    main()
