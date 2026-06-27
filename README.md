# apple-music-pipeline

Download a song from a link and have it appear in **Apple Music** automatically.

```bash
addsong "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

That one command downloads the audio, tags it (title, artist, cover art), and drops
it into Apple Music's watch folder. Apple Music imports it on its own a moment later.
No drag-and-drop, no manual import.

> Cross-platform: macOS, Windows, and Linux.
> On macOS / Windows / WSL the file lands in Apple Music's (or iTunes') "Automatically
> Add to ..." folder and the app imports it. On plain Linux there is no Apple Music
> app, so files are written to an output folder for you to import into any player.
> Downloads use [`yt-dlp`](https://github.com/yt-dlp/yt-dlp);
> conversion/tagging uses [`ffmpeg`](https://ffmpeg.org/). Only download content you
> have the right to.

## Setup

### Install

**Homebrew (macOS)** — installs `addsong` and pulls in `yt-dlp` and `ffmpeg`:

```bash
brew install YOURNAME/tap/addsong
```

<!-- Replace YOURNAME with your GitHub username once the tap is published.
     See RELEASE.md for the publish steps. -->

**Manual (any platform)** — install the two dependencies yourself, then drop the
script on your `PATH`:

```bash
# dependencies (pick one per platform):
#   macOS:  brew install yt-dlp ffmpeg
#   Win*:   choco install yt-dlp ffmpeg   (in Git Bash / WSL)
#   Debian: sudo apt install yt-dlp ffmpeg
#   Arch:   sudo pacman -S yt-dlp ffmpeg
mkdir -p ~/bin
mv addsong ~/bin/addsong
chmod +x ~/bin/addsong
```

If `~/bin` isn't already on your `PATH`, add it (then open a new terminal):

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc        # macOS (zsh)
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc       # Linux / Git Bash
```

### Confirm the watch folder

`addsong` drops tagged files into a watch folder that your music app scans.
The default is detected per platform — override with `ADDSONG_WATCH_DIR` only
if your library lives elsewhere.

**macOS** — Apple Music auto-imports from:

```
~/Music/Music/Media.localized/Automatically Add to Music.localized/
```

Open the **Music** app, drop any `.m4a`/`.mp3` into that folder, and it should
appear in your library within a couple of seconds. (Find the path under
**Music > Settings > Files** if your library isn't in the default location.)

> The first time `addsong` writes there, macOS may prompt your terminal for
> permission to access the Music folder. Click **Allow**.

**Windows** — needs [Git Bash](https://git-scm.com/downloads) (or WSL). The watch
folder is one of (the script probes both):

```
%USERPROFILE%\Music\Apple Music\Media\Automatically Add to Apple Music    (new Apple Music preview app)
%USERPROFILE%\Music\iTunes\iTunes Media\Automatically Add to iTunes       (legacy iTunes)
```

Open the Apple Music preview app (or iTunes) **at least once** so it creates its
library and watch folder, then re-run `addsong`. With the app running, files
import on the spot; with it closed, the next launch imports them.

> Use `.m4a` (the default). Legacy iTunes can't decode `.flac` and quietly
> moves such files to a `Not Added` subfolder instead of importing them.

**Linux / WSL without a Windows library** — there's no Apple Music app, so
`addsong` writes to an output folder you can import into any player:

```
~/Music/addsong/
```

The script creates this folder on first run and prints where it is. To use the
Apple Music watch folder from WSL instead, point at the Windows path:

```bash
export ADDSONG_WATCH_DIR="/mnt/c/Users/you/Music/Apple Music/Media/Automatically Add to Apple Music"
```

## Usage

```bash
# single track
addsong "https://www.youtube.com/watch?v=..."

# by name — no URL needed (top YouTube result)
addsong "rick astley never gonna give you up"

# top 3 search results
addsong --search 3 "80s disco mix"

# a whole playlist
addsong --playlist "https://www.youtube.com/playlist?list=..."

# no prompts, accept the scraped metadata as-is
addsong -y "https://youtu.be/..."
```

For a single track, `addsong` shows the scraped artist and title and lets you fix
them before import:

```
  Artist   Rick Astley
  Title    Never Gonna Give You Up

  [Enter] add    [e] edit    [s] skip
  >
```

Press **Enter** to accept, **e** to edit (blank keeps the current value), or **s**
to skip.

### Subscriptions

Pick a YouTube playlist once, then keep your library in sync as new tracks land:

```bash
# remember a playlist once
addsong subscribe "https://www.youtube.com/playlist?list=PL..."

# show what you're subscribed to
addsong list

# import any new tracks from every subscribed playlist
addsong sync
```

`sync` expands each subscribed playlist and imports only the tracks you haven't
imported before (re-using the same dedup ledger, so it's safe to re-run daily).
Flags compose with it just like a manual playlist run:

```bash
addsong sync --dry-run        # preview what sync would import
addsong sync -y               # no prompts
addsong sync --force          # re-import tracks even if already in the ledger
addsong sync --edit           # review each new track
```

Forget a playlist:

```bash
addsong unsubscribe "https://www.youtube.com/playlist?list=PL..."
```

The subscription file is plain text (one URL per line, `#` comments allowed) so
you can edit it by hand if you like:

```
~/.local/state/addsong/subscribed.tsv
```

### Options

| Flag           | Effect                                                       |
|----------------|-------------------------------------------------------------|
| `--search N`   | Treat the argument as a free-text YouTube search; import the top N (1-50) results. Default `1` when the argument is not a URL. No new dependencies. |
| `--playlist`   | Import every track in a playlist URL                         |
| `--from FILE`  | Read URLs (one per line) from `FILE`, or `-` for stdin       |
| `-y`, `--yes`  | Don't prompt; accept the scraped/cleaned metadata           |
| `--edit`       | Always prompt to review (even for each track in a playlist)  |
| `--force`      | Import even if the track was imported before                 |
| `--dry-run`    | Resolve and show metadata; download/import nothing           |
| `--quiet`      | Suppress info banners and per-track status lines (errors still print) |
| `--verbose`    | Surface `yt-dlp` / `ffmpeg` stderr for troubleshooting       |
| `--no-color`   | Disable colored output (also honors the `NO_COLOR` env var)  |
| `-h`,`--help`  | Show help                                                   |

Playlists and `--from` lists are non-interactive by default; add `--edit` to
review each track. `--from` skips blank lines and `#` comments, so a saved list
can be annotated:

```bash
# preview what a list would import, without downloading
addsong --from songs.txt --dry-run

# pipe in URLs from anywhere (pbpaste on macOS; xclip -o / powershell gcb on Linux/Win)
pbpaste | addsong --from -
```

### Settings

Configured with environment variables:

| Variable               | Purpose                            | Default                                |
|------------------------|------------------------------------|----------------------------------------|
| `ADDSONG_WATCH_DIR`    | Watch / output folder              | auto-detected per OS (see Setup)       |
| `ADDSONG_AUDIO_FORMAT` | Output audio format                | `m4a`                                  |
| `ADDSONG_LEDGER`       | Imported-tracks list (dedup)       | `~/.local/state/addsong/imported.tsv`  |
| `ADDSONG_SUBSCRIPTIONS`| Subscribed-playlists file          | `~/.local/state/addsong/subscribed.tsv`|
| `ADDSONG_RETRIES`      | Extra attempts on transient errors | `2`                                    |
| `ADDSONG_RETRY_DELAY`  | Base backoff seconds per attempt   | `3`                                    |
| `ADDSONG_CONFIG`       | Config file of `KEY=VALUE` defaults| `~/.config/addsong/config`             |

To set defaults once, put `KEY=VALUE` lines in `~/.config/addsong/config` (it is
parsed, not executed, so only `ADDSONG_*` keys are read). A real environment
variable always overrides the file:

```ini
ADDSONG_AUDIO_FORMAT=mp3
ADDSONG_WATCH_DIR="/Volumes/Music/Automatically Add to Music.localized"
```

## Notes

- **Progress feedback:** at a terminal, each track shows a spinner while it
  fetches info and downloads, then collapses to a single colored `Added` /
  `Skipped` / `Failed` line. The spinner is automatically suppressed when output
  isn't a terminal (pipes, CI) and under `--quiet` / `--verbose`.
- **Metadata** is cleaned automatically: junk like `(Official Video)`, `[4K]`,
  `(Lyrics)` is stripped, and `Artist - Title` is split out (falling back to the
  uploader as artist). When a source provides structured music tags (e.g. YouTube
  Music), the real track, artist, album, year, and track number are used as-is.
- **Sources:** any site `yt-dlp` supports works, including SoundCloud — just pass
  the URL. (Apple Music's own catalog is not a source; this imports downloaded
  audio into your library.)
- **Search-by-name** (no URL): pass a free-text query and `addsong` imports the
  top YouTube result (or top `N` with `--search N`). YouTube's top result isn't
  always the studio original — use `--edit` to review each hit, or `--dry-run`
  to preview what would import before committing.
- **Duplicates** are tracked by video ID, so re-runs skip songs already imported.
  Use `--force` to override.
- **Syncing to your phone** is handled by Apple, not this tool. Tracks have to
  upload from your computer to iCloud (they aren't in Apple's catalog), so keep
  the Mac/PC open and online, and make sure *Sync Library* is on for both
  devices. On Linux / WSL output-only mode there's no sync — move the file into
  your library of choice yourself.
- Some videos (private, region-locked, age-gated) may fail to download. Keep
  `yt-dlp` current (`brew upgrade yt-dlp` / `choco upgrade yt-dlp` /
  `sudo pacman -Syu yt-dlp` / distro upgrade) — an outdated version is the
  usual cause. Re-run with `--verbose` to see the underlying `yt-dlp` / `ffmpeg`
  error.

## Development

`addsong` is a single Bash script that guards `main()` behind a source check, so
its functions can be sourced and unit-tested. Continuous integration runs the
same two checks on every push:

```bash
brew install shellcheck bats-core   # one-time
shellcheck addsong                  # lint
bats test/                          # unit tests
```
