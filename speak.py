#!/usr/bin/env python3
"""
speak.py — Speak EPUB
Convert an EPUB file to an audiobook using Microsoft Edge TTS (free, high-quality neural voices).

Usage:
    python speak.py "book.epub"
    python speak.py "book.epub" --voice en-US-AriaNeural
    python speak.py "book.epub" --voice en-GB-SoniaNeural --output my_audiobook
    python speak.py "book.epub" --m4b
    python speak.py "book.epub" --m4a
    python speak.py --list-voices

Requirements:
    pip install ebooklib beautifulsoup4 edge-tts lxml
    ffmpeg must be on PATH for --m4b
"""

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    import edge_tts
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("\nInstall with:")
    print("    pip install ebooklib beautifulsoup4 edge-tts lxml")
    sys.exit(1)


def extract_chapters(epub_path: str) -> list[tuple[str, str]]:
    """Return list of (title, text) tuples for each chapter in spine order."""
    book = epub.read_epub(epub_path)
    chapters = []

    # Index documents by id, then walk the spine for correct reading order
    items_by_id = {item.id: item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}

    for item_id, _ in book.spine:
        item = items_by_id.get(item_id)
        if item is None:
            continue
        soup = BeautifulSoup(item.get_content(), "lxml")

        # Try to get chapter title from heading tags
        heading = soup.find(["h1", "h2", "h3"])
        title = heading.get_text(strip=True) if heading else item.get_name()

        # Remove script/style noise
        for tag in soup(["script", "style", "nav", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > 100:  # skip near-empty pages (TOC, cover, etc.)
            chapters.append((title, text))

    return chapters


async def tts_chapter(text: str, output_path: str, voice: str) -> None:
    """Convert text to speech and save as MP3."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


async def list_voices(all_languages: bool = False) -> None:
    voices = await edge_tts.list_voices()
    if not all_languages:
        voices = [v for v in voices if v["Locale"].startswith("en")]
    print(f"{'Name':<35} {'Gender':<8} {'Locale'}")
    print("-" * 60)
    for v in sorted(voices, key=lambda x: x["ShortName"]):
        print(f"{v['ShortName']:<35} {v['Gender']:<8} {v['Locale']}")
    if all_languages:
        print(f"\nTotal voices: {len(voices)}")
    else:
        print(f"\nTotal English voices: {len(voices)}")
        print("Use --all-languages to list voices for all languages.")


def build_m4b(output_dir: str, chapters: list[tuple[str, str]], mp3_paths: list[str], book_title: str, ext: str = "m4b") -> None:
    """Combine chapter MP3s into a single M4B/M4A with chapter markers using FFmpeg."""
    if not shutil.which("ffmpeg"):
        print(f"\nWarning: ffmpeg not found on PATH — skipping {ext.upper()} creation.")
        print("Install FFmpeg from https://ffmpeg.org/download.html and add it to PATH.")
        return

    print(f"\nBuilding {ext.upper()}...")

    # Write concat list
    concat_file = os.path.join(output_dir, "_concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in mp3_paths:
            # Use absolute paths so FFmpeg doesn't resolve relative to concat file location
            safe = os.path.abspath(p).replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe}'\n")

    # Probe duration of each MP3 to build chapter timestamps
    def get_duration_ms(path: str) -> int:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True
        )
        try:
            return int(float(result.stdout.strip()) * 1000)
        except ValueError:
            return 0

    def escape_ffmeta(s: str) -> str:
        """Escape special characters for the FFMETADATA1 format."""
        return re.sub(r'([=;#\\])', r'\\\1', s).replace('\n', '\\n')

    # Build FFMETADATA chapter block
    metadata_file = os.path.join(output_dir, "_metadata.txt")
    with open(metadata_file, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")
        f.write(f"title={escape_ffmeta(book_title)}\n\n")
        cursor = 0
        for (title, _), path in zip(chapters, mp3_paths):
            duration = get_duration_ms(path)
            f.write("[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={cursor}\n")
            f.write(f"END={cursor + duration}\n")
            f.write(f"title={escape_ffmeta(title)}\n\n")
            cursor += duration

    out_path = os.path.join(output_dir, f"{book_title}.{ext}")
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-i", metadata_file,
            "-map_metadata", "1",
            "-c:a", "aac", "-b:a", "64k",
            out_path
        ], check=True)
    finally:
        os.remove(concat_file)
        os.remove(metadata_file)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"{ext.upper()} saved: {out_path} ({size_mb:.1f} MB)")


async def convert(epub_path: str, output_dir: str, voice: str, m4b: bool, m4a: bool) -> None:
    chapters = extract_chapters(epub_path)
    if not chapters:
        print("No text chapters found in EPUB.")
        return

    os.makedirs(output_dir, exist_ok=True)
    total = len(chapters)
    print(f"Found {total} chapter(s). Converting with voice: {voice}")
    print(f"Output folder: {output_dir}\n")

    mp3_paths = []
    for i, (title, text) in enumerate(chapters, 1):
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:60].strip()
        filename = f"{i:03d}_{safe_title}.mp3"
        out_path = os.path.join(output_dir, filename)

        if os.path.exists(out_path):
            size_kb = os.path.getsize(out_path) // 1024
            print(f"[{i}/{total}] {title[:60]} (skipped, already exists, {size_kb} KB)")
        else:
            print(f"[{i}/{total}] {title[:60]}")
            if len(text) > 5000:
                print(f"  Warning: chapter is {len(text):,} chars — long chapters may be truncated by Edge TTS.")
            await tts_chapter(text, out_path, voice)
            size_kb = os.path.getsize(out_path) // 1024
            print(f"        -> {filename} ({size_kb} KB)")
        mp3_paths.append(out_path)

    print(f"\nDone! {total} MP3 files saved to: {output_dir}")

    if m4b or m4a:
        book_title = re.sub(r'[\\/:*?"<>|]', "_", Path(epub_path).stem)
        ext = "m4a" if m4a else "m4b"
        build_m4b(output_dir, chapters, mp3_paths, book_title, ext)


def main():
    parser = argparse.ArgumentParser(description="Speak EPUB: convert an EPUB file to an audiobook")
    parser.add_argument("epub", nargs="?", help="Path to the EPUB file")
    parser.add_argument(
        "--voice",
        default="en-GB-RyanNeural",
        help="Edge TTS voice name (default: en-GB-RyanNeural)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output folder name (default: <epub_name>_audiobook)",
    )
    parser.add_argument(
        "--m4b",
        action="store_true",
        help="Combine chapter MP3s into a single M4B audiobook file (requires ffmpeg)",
    )
    parser.add_argument(
        "--m4a",
        action="store_true",
        help="Combine chapter MP3s into a single M4A audiobook file (requires ffmpeg)",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available English TTS voices and exit",
    )
    parser.add_argument(
        "--all-languages",
        action="store_true",
        help="With --list-voices, show voices for all languages (not just English)",
    )
    args = parser.parse_args()

    if args.list_voices:
        asyncio.run(list_voices(all_languages=args.all_languages))
        return

    if not args.epub:
        parser.print_help()
        sys.exit(1)

    epub_path = Path(args.epub)
    if not epub_path.exists():
        print(f"File not found: {epub_path}")
        sys.exit(1)

    output_dir = args.output or (epub_path.stem + "_audiobook")

    asyncio.run(convert(str(epub_path), output_dir, args.voice, args.m4b, args.m4a))


if __name__ == "__main__":
    main()
