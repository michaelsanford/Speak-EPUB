# Contributing to Speak EPUB

Thanks for your interest in contributing!

## Running locally

```sh
git clone https://github.com/michaelsanford/Speak-EPUB.git
cd Speak-EPUB

python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

To test a conversion:

```sh
python speak.py "path/to/book.epub"
```

FFmpeg is only needed if you're working on `--m4b` / `--m4a` output.

## What makes a good PR

- **Fix a specific thing.** One bug or feature per PR keeps review focused.
- **Test your change.** Run through at least a basic conversion with a real EPUB and confirm it works end-to-end.
- **Keep diffs small.** Avoid reformatting unrelated code in the same PR.
- **Describe what and why** in the PR body, not just what the code does.

## Reporting issues

Use the issue templates — they ask for the right information up front and make it much faster to reproduce and fix problems.

## Questions

Open a [Discussion](https://github.com/michaelsanford/Speak-EPUB/discussions) rather than an issue for usage questions or ideas you're not sure about yet.
