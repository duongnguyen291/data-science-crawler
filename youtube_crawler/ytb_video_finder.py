from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from typing import Dict, Iterable, List, Set, Tuple

import requests

YOUTUBE_SEARCH_ENDPOINT = "https://www.youtube.com/results"
VIDEO_URL_PREFIX = "https://www.youtube.com/watch?v="
VIDEO_ID_PATTERN = re.compile(r'"videoId":"(?P<id>[a-zA-Z0-9_-]{11})"')

MUSIC_MV_HYPE_ARTISTS_VI: Tuple[str, ...] = (
    "Sơn Tùng M-TP",
    "Hồ Ngọc Hà",
    "MIN",
    "AMEE",
    "Hoàng Thùy Linh",
    "Đen Vâu",
    "Erik",
    "Hòa Minzy",
    "Noo Phước Thịnh",
    "Ngô Kiến Huy",
    "Bích Phương",
    "Tóc Tiên",
    "Trúc Nhân",
    "Jack J97",
    "Mono",
    "Orange",
    "LyLy",
    "Chillies",
)

MUSIC_MV_HYPE_ARTISTS_EN: Tuple[str, ...] = (
    "Taylor Swift",
    "Ed Sheeran",
    "Billie Eilish",
    "Dua Lipa",
    "Harry Styles",
    "Adele",
    "Olivia Rodrigo",
    "Ariana Grande",
    "Justin Bieber",
    "Drake",
    "Bruno Mars",
    "Beyoncé",
    "The Weeknd",
    "Sam Smith",
    "Coldplay",
    "Katy Perry",
    "Miley Cyrus",
    "SZA",
    "Lady Gaga",
)

LANGUAGE_TAGS: Dict[str, Dict[str, str]] = {
    "vi": {
        "music_top_chart": "MV chính thức, playlist nhạc hit thịnh hành",
        "music_live_concert": "live concert, tour, sân khấu lớn Việt Nam",
        "music_cover": "bản cover, acoustic, live session Việt",
        "music_reaction": "reaction, review MV Việt mới",
        "music_mv_hype": "MV nhạc Việt thịnh hành",
        "soundtrack": "OST, nhạc phim Việt",
        "movie_trailer": "trailer chính thức phim Việt sắp chiếu",
        "movie_review": "video review, phân tích phim Việt",
        "movie_scene_clip": "trích đoạn, clip ấn tượng phim Việt",
        "movie_interview": "hậu trường, phỏng vấn diễn viên ca sĩ Việt",
    },
    "en": {
        "movie_flop": "box office flop, worst movie, movie bomb, terrible film",
        "movie_worst": "worst movie of year, terrible movie, bad film, awful movie",
        "movie_disappointing": "disappointing movie, overrated film, movie letdown, underwhelming film",
        "movie_review_negative": "bad movie review, worst film analysis, terrible movie critique, negative film review",
        "movie_controversy": "controversial movie, movie scandal, problematic film, divisive movie",
        
        "rap_beef": "rap beef, diss track, rap feud, hip hop drama, rap war",
        "rap_controversial": "controversial rap song, problematic rap, divisive hip hop, controversial hip hop",
        "rap_worst": "worst rap song, terrible rap, bad hip hop, awful rap, worst hip hop",
        
        "music_flop": "worst song, music flop, bad music release, terrible song",
        "music_worst": "worst music video, terrible song, bad MV, awful music",
        "music_cringe": "cringe music video, embarrassing song, awkward MV, cringeworthy music",
        "music_controversy": "controversial music video, problematic song, music scandal, divisive MV",
        "music_review_negative": "bad music review, worst song critique, terrible album review, negative music review"
    },
}

"""
    "music_top_chart": "official US-UK MV, trending hit playlist",
    "music_live_concert": "live concert, tour, stadium show US-UK",
    "music_cover": "cover version, acoustic, live session US-UK",
    "music_reaction": "reaction to MV US-UK",
    "music_mv_hype": "major US-UK trending MV",
    "soundtrack": "OST, US-UK movie soundtrack",
    
    "movie_trailer": "official trailer upcoming movie US-UK",
    "movie_review": "movie review, analysis video US-UK",
    "movie_scene_clip": "US-UK movie scene highlight clip",
    "movie_interview": "behind the scenes, cast interview US-UK",
"""


def search_youtube(query: str, max_results: int) -> List[str]:
    """
    Query the public YouTube search page and return a list of video URLs.

    This implementation avoids the YouTube Data API and third-party wrappers so it
    keeps working in restricted environments (no proxies needed).
    """
    params = {"search_query": query, "hl": "vi"}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.5993.88 Safari/537.36"
        ),
        "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(
            YOUTUBE_SEARCH_ENDPOINT, params=params, headers=headers, timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[search] Failed for query '{query}': {exc}", file=sys.stderr)
        return []

    html = response.text
    result_urls: List[str] = []
    seen_ids: Set[str] = set()
    for match in VIDEO_ID_PATTERN.finditer(html):
        video_id = match.group("id")
        if video_id in seen_ids:
            continue
        seen_ids.add(video_id)
        result_urls.append(f"{VIDEO_URL_PREFIX}{video_id}")
        if len(result_urls) >= max_results:
            break

    if not result_urls:
        print(f"[search] No video IDs parsed for query '{query}'.", file=sys.stderr)
    return result_urls


def iter_tag_queries(language_code: str, tag: str, base_query: str) -> Iterable[Tuple[str, str]]:
    if tag == "music_mv_hype":
        artist_list = (
            MUSIC_MV_HYPE_ARTISTS_VI if language_code == "vi" else MUSIC_MV_HYPE_ARTISTS_EN
        )
        for artist in artist_list:
            yield f"{base_query} {artist}", artist
    else:
        yield base_query, ""


def collect_rows(
    language_code: str, tags: Dict[str, str], max_results: int, delay: float
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen_urls: set[str] = set()

    for tag, query in tags.items():
        for idx, (query_text, artist) in enumerate(
            iter_tag_queries(language_code, tag, query), start=1
        ):
            urls = search_youtube(query_text, max_results=max_results)
            for url in urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                rows.append({"tag": tag, "query": query_text, "url": url, "artist": artist})
            if delay:
                time.sleep(delay)

    return rows


def write_csv(rows: Iterable[Dict[str, str]], output_path: str) -> None:
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["tag", "artist", "query", "url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "tag": row.get("tag", ""),
                    "artist": row.get("artist", ""),
                    "query": row.get("query", ""),
                    "url": row.get("url", ""),
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch YouTube video URLs grouped by entertainment tags in VI and EN."
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum number of search results to request per tag (default: 20).",
    )
    parser.add_argument(
        "--output-vi",
        default=os.path.join(os.getcwd(), "youtube_videos_vi.csv"),
        help="Output CSV path for Vietnamese queries (default: ./youtube_videos_vi.csv).",
    )
    parser.add_argument(
        "--output-en",
        default=os.path.join(os.getcwd(), "youtube_videos_en.csv"),
        help="Output CSV path for English queries (default: ./youtube_videos_en.csv).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay in seconds between tag searches to avoid throttling (default: 0.25).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    vi_rows = collect_rows(
        "vi", LANGUAGE_TAGS["vi"], max_results=args.max_results, delay=args.delay
    )
    en_rows = collect_rows(
        "en", LANGUAGE_TAGS["en"], max_results=args.max_results, delay=args.delay
    )

    if not vi_rows and not en_rows:
        print("No videos collected for either language. Check network connectivity or queries.", file=sys.stderr)
        sys.exit(1)

    if vi_rows:
        write_csv(vi_rows, args.output_vi)
        print(
            f"[VI] Collected {len(vi_rows)} unique video URLs across {len(LANGUAGE_TAGS['vi'])} tags."
        )
        print(f"[VI] CSV saved to: {args.output_vi}")
    else:
        print("[VI] No rows collected.", file=sys.stderr)

    if en_rows:
        write_csv(en_rows, args.output_en)
        print(
            f"[EN] Collected {len(en_rows)} unique video URLs across {len(LANGUAGE_TAGS['en'])} tags."
        )
        print(f"[EN] CSV saved to: {args.output_en}")
    else:
        print("[EN] No rows collected.", file=sys.stderr)


if __name__ == "__main__":
    main()
