# YTtranscript

Simple helpers for grabbing subtitle text from a YouTube video.

## Requirements

- Python 3.9+
- [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/)  
  Install via `py -m pip install youtube-transcript-api`

## download_subtitles.py

`download_subtitles.py` mirrors the workflows described in 
`FetchedTranscript` via the built-in formatter classes.

Detect whether subtitles exist for a given YouTube URL and download them if they do:

```powershell
python download_subtitles.py "<video url>" `
  --output captions.txt `
  --languages en,zh-Hant `
  --translate zh-Hant `
  --format json `
  --preserve-formatting
```

Arguments:

- `url` (positional) - YouTube video link.
- `--output / -o` - Optional path for the saved subtitle text (defaults to `captions.txt`).
- `--languages / -l` - Optional comma separated list of language codes in preference order (README: *Retrieve different languages*).
- `--translate` - Translate the transcript to this language code before saving (README: *Translate transcript*).
- `--format` - Output format powered by the official formatter classes (`text`, `pretty`, `json`, `srt`, `vtt`).
- `--preserve-formatting` - Keep HTML markers (`<i>`, `<b>`, etc.) when fetching.

When subtitles are available the script prints every detected language, the final language that was downloaded
(translated or not), and writes the formatter output to the requested file.
