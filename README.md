# Speak EPUB

Convert any EPUB file into a spoken-word audiobook using Microsoft Edge's free neural text-to-speech voices. Outputs one MP3 per chapter, with an optional single M4B file with chapter markers.

## How it works

1. Extracts text from each chapter in the EPUB (EPUBs are ZIP files containing HTML)
2. Sends each chapter's text to Microsoft Edge TTS (the same engine behind Windows Narrator and Edge's Read Aloud) — free, no API key required
3. Saves each chapter as a numbered MP3
4. Optionally combines all chapters into a single `.m4b` audiobook file with chapter markers using FFmpeg

## Requirements

- Python 3.10+
- FFmpeg on your PATH (only needed for `--m4b`)

## Installation

```powershell
# Clone or download the project, then:
cd speak-epub

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**For M4B output**, install FFmpeg:
```powershell
winget install ffmpeg
```

## Usage

```powershell
# Basic conversion (outputs chapter MP3s into a folder)
python speak.py "path\to\book.epub"

# Also produce a single M4B audiobook with chapter markers
python speak.py "path\to\book.epub" --m4b

# Choose a different voice
python speak.py "path\to\book.epub" --voice en-US-AriaNeural

# Custom output folder name
python speak.py "path\to\book.epub" --output my_audiobook

# List all available English voices
python speak.py --list-voices

# List voices for all languages
python speak.py --list-voices --all-languages
```

The default voice is `en-GB-RyanNeural` (British male). Run `--list-voices` to browse available English voices, or add `--all-languages` to see all languages.

## Output

```
my_book_audiobook/
├── 001_Introduction.mp3
├── 002_Chapter_One.mp3
├── 003_Chapter_Two.mp3
├── ...
└── my_book.m4b          # only with --m4b
```

If you re-run the script, any chapter MP3 that already exists is skipped — only missing chapters are re-generated. This means if the M4B step fails, you can re-run with `--m4b` and it won't redo all the TTS work.

## Voices

A selection of recommended voices:

| Voice | Gender | Accent |
|---|---|---|
| `en-GB-RyanNeural` | Male | British |
| `en-GB-SoniaNeural` | Female | British |
| `en-US-AriaNeural` | Female | American |
| `en-US-GuyNeural` | Male | American |
| `en-AU-WilliamMultilingualNeural` | Male | Australian |

Run `python speak.py --list-voices` for the full English list, or `--list-voices --all-languages` for all languages.

## License

MIT — see [LICENSE.md](LICENSE.md)
