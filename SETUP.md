# Setup

`addsong` works on macOS, Windows (via Git Bash or WSL), and Linux (output-only
— there is no Apple Music app on Linux). It needs two command-line tools and a
watch folder.

## Step 1 — Install dependencies

Install [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) (downloads the audio) and
[`ffmpeg`](https://ffmpeg.org/) (converts and tags it).

```bash
# macOS — Homebrew
brew install yt-dlp ffmpeg

# Windows (Git Bash or WSL) — Chocolatey, Scoop, or winget
choco install yt-dlp ffmpeg        # or:  scoop install yt-dlp ffmpeg
# winget install yt-dlp.yt-dlp Gyan.FFmpeg

# Debian / Ubuntu
sudo apt install yt-dlp ffmpeg

# Arch
sudo pacman -S yt-dlp ffmpeg
```

Keep `yt-dlp` current — an outdated version is the most common cause of failed
downloads:

```bash
brew upgrade yt-dlp              # macOS
choco upgrade yt-dlp             # Windows (Chocolatey)
sudo pacman -Syu yt-dlp           # Arch
# Debian/Ubuntu: download the latest release manually if the apt version is stale
```

## Step 2 — Confirm the watch folder

`addsong` auto-detects the watch folder per platform. You only need to set
`ADDSONG_WATCH_DIR` if your library lives somewhere non-standard.

### macOS

Apple Music auto-imports from this folder (the default `addsong` uses):

```
~/Music/Music/Media.localized/Automatically Add to Music.localized/
```

Open the **Music** app, drag any `.m4a` or `.mp3` into that folder, and it
should appear in your library within a couple of seconds. If your library lives
elsewhere, find the path under **Music > Settings > Files** ("Music Media folder
location"), then point `addsong` at the *Automatically Add to Music* folder inside
it:

```bash
export ADDSONG_WATCH_DIR="/path/to/Automatically Add to Music.localized"
```

The first time `addsong` writes there, macOS may prompt your terminal for
permission to access the Music folder. Click **Allow**.

### Windows (Git Bash or WSL)

`addsong` probes both watch folders in order and uses the first that exists:

```
%USERPROFILE%\Music\Apple Music\Media\Automatically Add to Apple Music   (Apple Music preview app)
%USERPROFILE%\Music\iTunes\iTunes Media\Automatically Add to iTunes      (legacy iTunes)
```

Open the Apple Music preview app (or iTunes) **at least once** so it creates
its library and watch folder, then re-run `addsong`. With the app running,
files are imported immediately; with it closed, the next launch picks them up.

> Use the default `.m4a`. Legacy iTunes can't decode `.flac` and silently moves
> such files to a `Not Added` subfolder instead of importing them.

If you relocated your media library (e.g. to another drive), point at the watch
folder inside it:

```bash
export ADDSONG_WATCH_DIR="D:/iTunes/iTunes Media/Automatically Add to iTunes"
```

### WSL (using the Windows Apple Music library)

The script globs `/mnt/c/Users/*/Music/Apple Music/Media/Automatically Add to
Apple Music` and picks the first match. If your library isn't auto-detected,
set the path explicitly:

```bash
export ADDSONG_WATCH_DIR="/mnt/c/Users/you/Music/Apple Music/Media/Automatically Add to Apple Music"
```

### Linux (output-only, no Apple Music app)

There is no Apple Music app on Linux. `addsong` writes tagged files to an
output folder you can import into any media player:

```
~/Music/addsong/
```

The folder is created on first run and the path is printed. To use a different
folder (for example your media server's library):

```bash
export ADDSONG_WATCH_DIR="/srv/music/inbox"
```

## Step 3 — Install the command

Put `addsong` on your `PATH`:

```bash
mkdir -p ~/bin
mv addsong ~/bin/addsong
chmod +x ~/bin/addsong
```

If `~/bin` isn't on your `PATH`, add it (then open a new terminal):

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc        # macOS (zsh)
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc       # Linux / Git Bash
```

Confirm it's installed:

```bash
addsong --version
```

## Configuration

All settings are environment variables (see `addsong --help`):

| Variable               | Purpose                       | Default                                |
|------------------------|-------------------------------|----------------------------------------|
| `ADDSONG_WATCH_DIR`    | Watch / output folder         | auto-detected per OS (see Step 2)      |
| `ADDSONG_AUDIO_FORMAT` | Output audio format           | `m4a`                                  |
| `ADDSONG_LEDGER`       | Imported-tracks list (dedup)  | `~/.local/state/addsong/imported.tsv`  |
| `ADDSONG_RETRIES`      | Extra attempts on transient   | `2`                                    |
| `ADDSONG_RETRY_DELAY`  | Base backoff seconds           | `3`                                    |
| `ADDSONG_CONFIG`       | Config file of `KEY=VALUE`    | `~/.config/addsong/config`             |

Put `KEY=VALUE` lines in `~/.config/addsong/config` to set defaults once (it's
parsed, not executed — only `ADDSONG_*` keys are read). A real environment
variable always overrides the file:

```ini
ADDSONG_AUDIO_FORMAT=mp3
ADDSONG_WATCH_DIR="/Volumes/Music/Automatically Add to Music.localized"
```