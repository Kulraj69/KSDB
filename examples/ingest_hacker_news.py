"""
Ingest recent public Hacker News stories into KSdb.

This is intentionally API-key free. It uses the public Algolia-powered HN
Search API, turns each story into a searchable document, and stores source
metadata so you can filter or cite results later.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ksdb import Client


HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"


def fetch_stories(query: str, limit: int) -> List[Dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "tags": "story",
            "hitsPerPage": limit,
        }
    )
    request = urllib.request.Request(
        f"{HN_SEARCH_URL}?{params}",
        headers={"User-Agent": "ksdb-live-data-example/1.0"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload.get("hits", [])


def story_to_document(story: Dict[str, Any], query: str) -> Dict[str, Any]:
    title = story.get("title") or story.get("story_title") or "Untitled story"
    url = story.get("url") or story.get("story_url") or ""
    text = story.get("story_text") or ""

    document = "\n".join(
        part
        for part in [
            f"Title: {title}",
            f"URL: {url}" if url else "",
            text.strip(),
        ]
        if part
    )

    return {
        "id": f"hn-{story['objectID']}",
        "document": document,
        "metadata": {
            "source": "hacker_news",
            "query": query,
            "title": title,
            "url": url,
            "author": story.get("author"),
            "created_at": story.get("created_at"),
            "points": story.get("points") or 0,
            "num_comments": story.get("num_comments") or 0,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest recent Hacker News stories into KSdb")
    parser.add_argument("--query", default="vector database OR RAG", help="HN search query")
    parser.add_argument("--limit", type=int, default=20, help="Number of stories to fetch")
    parser.add_argument("--collection", default="live_hacker_news", help="KSdb collection name")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="KSdb server URL")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print stories without ingesting")
    args = parser.parse_args()

    stories = fetch_stories(args.query, args.limit)
    records = [story_to_document(story, args.query) for story in stories if story.get("objectID")]

    if args.dry_run:
        for record in records:
            print(f"{record['id']}: {record['metadata']['title']}")
        return

    client = Client(args.url)
    collection = client.get_or_create_collection(args.collection, metadata={"source": "hacker_news"})
    result = collection.add(
        ids=[record["id"] for record in records],
        documents=[record["document"] for record in records],
        metadatas=[record["metadata"] for record in records],
        deduplicate=True,
        extract_graph=False,
    )

    print(f"Ingested {result.get('count', 0)} stories into '{args.collection}'")
    print(f"Skipped {result.get('skipped', 0)} likely duplicates")


if __name__ == "__main__":
    main()
