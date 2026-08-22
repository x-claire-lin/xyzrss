from pathlib import Path
import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone


SOURCE_BASE = "https://feed.xyzfm.space/"
OUTPUT_DIR = Path("docs")
FEEDS_FILE = Path("feeds.txt")
INDEX_FILE = OUTPUT_DIR / "feeds.json"

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; xyzrss/1.0; "
    "+https://github.com/x-claire-lin/xyzrss)"
)

FEED_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]+$"
)


def read_feeds():
    """
    Read feeds.txt.

    Format:

        feed_id # Podcast Name
    """

    if not FEEDS_FILE.exists():
        raise FileNotFoundError(
            "feeds.txt not found"
        )

    feeds = []

    lines = FEEDS_FILE.read_text(
        encoding="utf-8"
    ).splitlines()

    for line_number, line in enumerate(
        lines,
        start=1
    ):
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        parts = line.split("#", 1)

        feed_id = parts[0].strip()

        title = ""

        if len(parts) > 1:
            title = parts[1].strip()

        if not FEED_ID_PATTERN.fullmatch(feed_id):
            print(
                f"WARNING: invalid feed ID "
                f"on line {line_number}: "
                f"{feed_id}"
            )

            continue

        feeds.append(
            {
                "id": feed_id,
                "title": title or feed_id,
            }
        )

    return feeds


def fetch_feed(feed_id):
    """
    Download one Xiaoyuzhou RSS feed.
    """

    url = (
        SOURCE_BASE +
        feed_id
    )

    print(f"Fetching: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, "
                "application/xml, "
                "text/xml, "
                "*/*"
            ),
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        data = response.read()

    if not data:
        raise RuntimeError(
            "Empty response"
        )

    print(
        f"Downloaded {len(data)} bytes"
    )

    return data


def fix_feed(data):
    """
    Convert audio/mp4 enclosure MIME type
    to audio/x-m4a.

    This is the only transformation
    performed on the original RSS.
    """

    # Xiaoyuzhou feeds are normally UTF-8.
    # Decode with replacement so that a
    # single malformed byte does not crash
    # the entire workflow.
    text = data.decode(
        "utf-8",
        errors="replace"
    )

    # Replace both:
    #
    # type="audio/mp4"
    #
    # and:
    #
    # type='audio/mp4'
    #
    # without changing anything else.
    text = re.sub(
        r'(\btype\s*=\s*["\'])audio/mp4(["\'])',
        r'\1audio/x-m4a\2',
        text,
        flags=re.IGNORECASE
    )

    return text.encode(
        "utf-8"
    )


def write_feeds_json(feeds):
    """
    Generate docs/feeds.json.

    The website uses this file to display
    the current podcast list.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    items = []

    for feed in feeds:

        feed_id = feed["id"]

        items.append(
            {
                "id": feed_id,

                "title": feed["title"],

                "source":
                    SOURCE_BASE +
                    feed_id,

                "rss":
                    f"{feed_id}.xml"
            }
        )

    payload = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "feeds": items
    }

    INDEX_FILE.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Written: {INDEX_FILE}"
    )


def remove_deleted_feeds(
    active_ids
):
    """
    Remove XML files that are no longer
    present in feeds.txt.
    """

    active_ids = set(
        active_ids
    )

    if not OUTPUT_DIR.exists():
        return

    for xml_file in OUTPUT_DIR.glob(
        "*.xml"
    ):

        feed_id = xml_file.stem

        if feed_id not in active_ids:

            print(
                f"Removing: {xml_file}"
            )

            xml_file.unlink()


def update_feed(feed_id):
    """
    Update one feed.
    """

    data = fetch_feed(
        feed_id
    )

    fixed = fix_feed(
        data
    )

    output_file = (
        OUTPUT_DIR /
        f"{feed_id}.xml"
    )

    output_file.write_bytes(
        fixed
    )

    print(
        f"Written: {output_file}"
    )


def update_all():
    """
    Update every feed in feeds.txt.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    feeds = read_feeds()

    if not feeds:
        raise RuntimeError(
            "No valid feeds found "
            "in feeds.txt"
        )

    active_ids = [
        feed["id"]
        for feed in feeds
    ]

    remove_deleted_feeds(
        active_ids
    )

    success = 0
    failed = 0

    for feed in feeds:

        feed_id = feed["id"]

        try:

            update_feed(
                feed_id
            )

            success += 1

        except Exception as error:

            failed += 1

            print(
                f"ERROR: {feed_id}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

    write_feeds_json(
        feeds
    )

    print()
    print(
        "================================"
    )

    print(
        f"Total:    {len(feeds)}"
    )

    print(
        f"Success:  {success}"
    )

    print(
        f"Failed:   {failed}"
    )

    print(
        "================================"
    )

    # If even one feed succeeded,
    # the workflow can still publish
    # the successfully updated feeds.
    #
    # If everything failed, however,
    # the workflow should fail so that
    # GitHub clearly reports the problem.
    if success == 0:

        raise RuntimeError(
            "All RSS feeds failed to update."
        )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Generate Xiaoyuzhou RSS proxy feeds."
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--all",
        action="store_true",
        help="Update all feeds."
    )

    group.add_argument(
        "--feed",
        help="Update one feed."
    )

    args = parser.parse_args()

    if args.all:

        update_all()

    elif args.feed:

        if not FEED_ID_PATTERN.fullmatch(
            args.feed
        ):
            raise ValueError(
                f"Invalid feed ID: "
                f"{args.feed}"
            )

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        update_feed(
            args.feed
        )

        feeds = read_feeds()

        write_feeds_json(
            feeds
        )


if __name__ == "__main__":
    main()
