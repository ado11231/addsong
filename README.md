<h3 align="center">addsong</h3>

<p align="center">
  <a href="https://pypi.org/project/addsong/"><img src="assets/badges/pypi.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="assets/badges/python.svg" alt="Python versions"></a>
  <a href="https://github.com/ado11231/addsong/blob/main/LICENSE"><img src="assets/badges/license.svg" alt="License"></a>
  <a href="https://github.com/yt-dlp/yt-dlp"><img src="assets/badges/ytdlp.svg" alt="Powered by yt-dlp"></a>
  <a href="https://ffmpeg.org/"><img src="assets/badges/ffmpeg.svg" alt="Tagged with ffmpeg"></a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="addsong demo" width="600">
</p>

<p align="center"><b>Paste a link and the song shows up in Apple Music.</b></p>

**addsong** takes a song name or a YouTube link. It downloads the track, tags it
with the title, artist, and cover art, then drops it into Apple Music. No
dragging files around, just a single command.

```bash
addsong "songname"
addsong "https://www.youtube.com/watch?v=..."
```

## Installation

You need Python 3.11 or newer, yt-dlp
and ffmpeg. **addsong** itself is a Python package you install with pipx.

### 1. Install **addsong**

```bash
pipx install addsong
```

### 2. Install yt-dlp and ffmpeg

**macOS** <img src="assets/macos.svg" height="16" align="absmiddle" style="position: relative; top: -2px;">

```bash
brew install yt-dlp ffmpeg
```

**Linux** <img src="assets/linux.svg" height="16" align="absmiddle" style="position: relative; top: -2px;">

```bash
sudo <package manager> ffmpeg && pipx install yt-dlp
```

**Windows** <img src="assets/windows.svg" height="16" align="absmiddle" style="position: relative; top: -2px;"> (PowerShell)

```powershell
winget install yt-dlp.yt-dlp Gyan.FFmpeg
```

### 3. Check it

```bash
addsong --version
```

## Updating

```bash
pipx upgrade addsong
```

With pip instead of pipx, run `python -m pip install --user --upgrade addsong`.


## Run Command

```bash
addsong "songname"
```

## Commands


| Command                        | What it does                                    |
| ------------------------------ | ----------------------------------------------- |
| `addsong "name"`               | Add the top search result                       |
| `addsong "<link>"`             | Add a specific video                            |
| `addsong --results 3 "name"`   | Add the top 3 search results                    |
| `addsong --playlist "<link>"`  | Add a whole playlist                            |
| `addsong --from list.txt`      | Add every link in a file                        |
| `addsong subscribe "<link>"`   | Follow a playlist                               |
| `addsong sync`                 | Add new songs from playlists you follow         |
| `addsong list`                 | Show playlists you follow                       |
| `addsong unsubscribe "<link>"` | Stop following a playlist                       |
| `addsong forget`               | Forget everything added so it can be re-added   |



## Flags


| Flag                    | What it does                                           |
| ----------------------- | ------------------------------------------------------ |
| `-y`                    | Don't ask, just add it                                 |
| `--review`              | Always pause to fix the title or artist first          |
| `--reimport`            | Add a song again even if you already have it           |
| `--dry-run`             | Show what would happen without downloading            |
| `--format FMT`          | Output format, `m4a` (default), `mp3`, `flac`, `opus`  |
| `--quality N`           | Audio quality 0 to 10, 0 is best and the default       |
| `--notify`              | Pop a desktop notification as each song imports        |
| `--quiet` / `--verbose` | Show less or more output                               |
| `--help`                | Full list of commands and options                      |


Set environment variables like `ADDSONG_WATCH_DIR` to change defaults. Run
`addsong --help` for the full list.
