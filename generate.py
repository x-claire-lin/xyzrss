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

USER_AGENT = "xyzrss/3.0 (+https://github.com/x-claire-lin/xyzrss)"

FEED_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def fetch_feed(feed_id):
    """Download the original Xiaoyuzhou RSS feed."""
    url = SOURCE_BASE + feed_id

    print(f"Fetching: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
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
    """Find a direct child by local XML name."""
    if element is None:
        return None

    for child in element:
        if local_name(child.tag).lower() == name.lower():
            return child

    return None


def get_text(element):
    """Return stripped element text."""
    if element is None:
        return ""

    return (element.text or "").strip()


def parse_metadata(data, feed_id):
    """Extract basic podcast metadata from RSS."""
    root = ET.fromstring(data)

    root_name = local_name(root.tag).lower()

    if root_name == "rss":
        channel = find_child(root, "channel")
    elif root_name == "channel":
        channel = root
    else:
        # Basic Atom fallback.
        channel = root

    title = ""
    image = ""
    description = ""

    if channel is not None:
        title = get_text(find_child(channel, "title"))
        description = get_text(find_child(channel, "description"))

        # Standard RSS image.
        image_element = find_child(channel, "image")

        if image_element is not None:
            image = get_text(find_child(image_element, "url"))

        # iTunes / Atom style image with href.
        if not image:
            for element in channel.iter():
                if local_name(element.tag).lower() == "image":
                    href = element.attrib.get("href", "").strip()

                    if href:
                        image = href
                        break

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


def fix_feed(data):
    """
    Make Xiaoyuzhou enclosure MIME types compatible with
    podcast applications that expect audio/x-m4a.

    audio/mp4 -> audio/x-m4a
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

    for line_number, line in enumerate(
        FEEDS_FILE.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        parts = line.split("#", 1)

        feed_id = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ""

        if not FEED_ID_PATTERN.fullmatch(feed_id):
            print(
                f"WARNING: skipping invalid feed ID "
                f"on line {line_number}: {feed_id}"
            )
            continue

        feeds.append(
            {
                "id": feed_id,
                "title": title,
            }
        )

    return feeds


def load_existing_metadata():
    """Load previously generated feed metadata."""
    if not INDEX_FILE.exists():
        return []

    try:
        data = json.loads(
            INDEX_FILE.read_text(encoding="utf-8")
        )

        feeds = data.get("feeds", [])

        if isinstance(feeds, list):
            return feeds

    except Exception as error:
        print(f"WARNING: unable to read existing feeds.json: {error}")

    return []


def write_feed_metadata(feed_metadata):
    """Write docs/feeds.json."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    feed_metadata = sorted(
        feed_metadata,
        key=lambda item: item.get("title", "").lower(),
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feeds": feed_metadata,
    }

    INDEX_FILE.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Written: {INDEX_FILE}")


def remove_deleted_feeds(active_feed_ids):
    """
    Remove generated XML files that are no longer listed in feeds.txt.
    """
    active_feed_ids = set(active_feed_ids)

    for xml_file in OUTPUT_DIR.glob("*.xml"):
        feed_id = xml_file.stem

        if feed_id not in active_feed_ids:
            print(f"Removing deleted feed: {xml_file}")
            xml_file.unlink()


def update_single(feed_id):
    """Update one feed."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    original = fetch_feed(feed_id)
    fixed = fix_feed(original)

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
    """Update all feeds listed in feeds.txt."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    feeds = read_feeds()

    if not feeds:
        raise RuntimeError("No valid feed IDs found")

    active_feed_ids = [feed["id"] for feed in feeds]

    remove_deleted_feeds(active_feed_ids)

    existing_metadata = load_existing_metadata()

    existing_by_id = {
        item.get("id"): item
        for item in existing_metadata
        if item.get("id")
    }

    metadata = []

    success_count = 0
    failure_count = 0

    for feed in feeds:
        feed_id = feed["id"]

        try:
            original = fetch_feed(feed_id)
            fixed = fix_feed(original)

            output_file = OUTPUT_DIR / f"{feed_id}.xml"

            output_file.write_bytes(fixed)

            item = parse_metadata(
                original,
                feed_id,
            )

            # Prefer the manually supplied name in feeds.txt.
            if feed["title"]:
                item["title"] = feed["title"]

            metadata.append(item)

            success_count += 1

            print(f"Updated: {output_file}")

        except Exception as error:
            failure_count += 1

            print(
                f"ERROR processing {feed_id}: {error}"
            )

            # Preserve the previously generated feed metadata.
            previous = existing_by_id.get(feed_id)

            if previous:
                if feed["title"]:
                    previous["title"] = feed["title"]

                metadata.append(previous)

                print(
                    f"Preserved previous metadata for {feed_id}"
                )
            else:
                print(
                    f"No previous metadata available for {feed_id}"
                )

    write_feed_metadata(metadata)

    print()
    print("========================================")
    print("RSS generation complete")
    print(f"Successful: {success_count}")
    print(f"Failed:     {failure_count}")
    print(f"Total:      {len(feeds)}")
    print("========================================")

    # Do not fail the entire GitHub Action just because one
    # podcast temporarily failed.
    if success_count == 0:
        raise RuntimeError(
            "All feeds failed to update."
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate Anytime-compatible "
            "Xiaoyuzhou RSS feeds."
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

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
            raise ValueError(
                f"Invalid feed ID: {args.feed}"
            )

        update_single(args.feed)


if __name__ == "__main__":
    main()

