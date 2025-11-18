"""Download YouTube subtitles following the official youtube-transcript-api README.

Patterns used inside this script mirror the documented API usage:
https://github.com/jdepoix/youtube-transcript-api#api
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.formatters import (
    JSONFormatter,
    PrettyPrintFormatter,
    SRTFormatter,
    TextFormatter,
    WebVTTFormatter,
)

VIDEO_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{11}")
FORMATTERS = {
    "text": TextFormatter,
    "pretty": PrettyPrintFormatter,
    "json": JSONFormatter,
    "srt": SRTFormatter,
    "vtt": WebVTTFormatter,
}


def extract_video_id(url: str) -> str:
    """Extract the 11-character YouTube video id from a URL."""
    parsed = urlparse(url)

    if parsed.netloc.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]
        if VIDEO_ID_PATTERN.fullmatch(candidate or ""):
            return candidate

    query_id = parse_qs(parsed.query).get("v", [""])[0]
    if VIDEO_ID_PATTERN.fullmatch(query_id):
        return query_id

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"watch", "live", "shorts"}:
        candidate = path_parts[1]
        if VIDEO_ID_PATTERN.fullmatch(candidate):
            return candidate

    match = VIDEO_ID_PATTERN.search(url)
    if match:
        return match.group(0)

    raise ValueError("Could not detect a valid YouTube video id from the provided URL.")


def parse_language_preferences(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    languages = [code.strip() for code in raw.split(",") if code.strip()]
    if not languages:
        return None
    return languages


def collect_available_languages(transcripts) -> List[str]:
    return [t.language_code for t in transcripts]


def pick_transcript(transcript_list, languages: Optional[List[str]], fallback_codes: List[str]):
    if languages:
        try:
            return transcript_list.find_transcript(languages)
        except NoTranscriptFound:
            pass
    if not fallback_codes:
        raise NoTranscriptFound("No subtitles published for this video.")
    return transcript_list.find_transcript(fallback_codes)


def fetch_transcript_data(
    api: YouTubeTranscriptApi,
    video_id: str,
    languages: Optional[List[str]],
    translate_to: Optional[str],
    preserve_formatting: bool,
):
    transcript_list = api.list(video_id)
    transcripts = list(transcript_list)
    if not transcripts:
        raise NoTranscriptFound("This video does not expose any transcripts.")

    available_codes = collect_available_languages(transcripts)
    transcript = pick_transcript(transcript_list, languages, available_codes)

    if translate_to:
        if not transcript.is_translatable:
            raise NoTranscriptFound("This transcript cannot be translated.")
        supported_translations = {
            lang["language_code"] for lang in transcript.translation_languages or []
        }
        if supported_translations and translate_to not in supported_translations:
            raise NoTranscriptFound(
                f"Transcript cannot be translated to '{translate_to}'. "
                f"Available targets: {', '.join(sorted(supported_translations))}"
            )
        transcript = transcript.translate(translate_to)

    fetched = transcript.fetch(preserve_formatting=preserve_formatting)
    return fetched, transcript.language_code, available_codes


def format_transcript_text(fetched, format_name: str) -> str:
    formatter_cls = FORMATTERS[format_name]
    formatter = formatter_cls()
    extra_kwargs = {"indent": 2} if format_name == "json" else {}
    return formatter.format_transcript(fetched, **extra_kwargs)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect and download YouTube subtitles using youtube-transcript-api."
    )
    parser.add_argument("url", help="Full YouTube video URL.")
    parser.add_argument(
        "-o",
        "--output",
        default="captions.txt",
        help="Where to save the formatted transcript (default: captions.txt).",
    )
    parser.add_argument(
        "-l",
        "--languages",
        help="Comma separated list of language codes ordered by preference (e.g. en,zh-Hant).",
    )
    parser.add_argument(
        "--translate",
        help="Translate the selected transcript to this language code before saving.",
    )
    parser.add_argument(
        "--format",
        choices=sorted(FORMATTERS.keys()),
        default="text",
        help="Output format powered by the formatters described in the official README.",
    )
    parser.add_argument(
        "--preserve-formatting",
        action="store_true",
        help="Keep HTML formatting markers when fetching the transcript.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    languages = parse_language_preferences(args.languages)
    api = YouTubeTranscriptApi()

    try:
        fetched, selected_language, available_languages = fetch_transcript_data(
            api=api,
            video_id=extract_video_id(args.url),
            languages=languages,
            translate_to=args.translate,
            preserve_formatting=args.preserve_formatting,
        )
        formatted_text = format_transcript_text(fetched, args.format)
    except ValueError as error:
        print(f"Invalid URL: {error}")
        return 1
    except TranscriptsDisabled:
        print("Subtitles are disabled for this video.")
        return 2
    except NoTranscriptFound as error:
        print(f"No subtitles available: {error}")
        return 3
    except VideoUnavailable:
        print("Video is unavailable.")
        return 4
    except Exception as error:
        print(f"Unexpected error while downloading subtitles: {error}")
        return 5

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(formatted_text, encoding="utf-8")

    print("Subtitles detected!")
    print(f"Available languages: {', '.join(available_languages)}")
    if args.translate:
        print(f"Downloaded language (translated): {args.translate}")
    else:
        print(f"Downloaded language: {selected_language}")
    print(f"Saved to: {output_path}")
    print(f"Format: {args.format}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
