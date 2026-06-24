# apple-music-pipeline

Download a song from a link and have it appear in **Apple Music** automatically.

```bash
addsong "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

That one command downloads the audio, tags it (title, artist, cover art), and drops
it into Apple Music's watch folder. Apple Music imports it on its own a moment later.
No drag-and-drop, no manual import.

> macOS only. Downloads use [`yt-dlp`](https://github.com/yt-dlp/yt-dlp);
> conversion/tagging uses [`ffmpeg`](https://ffmpeg.org/). Only download content you
> have the right to.

## Setup

**1. Install the tools** (needs [Homebrew](https://brew.sh)):

```bash
brew install yt-dlp ffmpeg
```

**2. Install the command** onto your `PATH`:

```bash
mkdir -p ~/bin
mv addsong ~/bin/addsong
chmod +x ~/bin/addsong
```

If `~/bin` isn't already on your `PATH`, add it (then open a new terminal):

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
```

**3. Confirm the watch folder works.** Apple Music auto-imports anything dropped into:

```
~/Music/Music/Media.localized/Automatically Add to Music.localized/
```

Open the **Music** app, drop any `.m4a`/`.mp3` into that folder, and it should appear
in your library within a couple seconds. If it does, you're ready. (If your library
lives elsewhere, find the path in **Music > Settings > Files** and set
`ADDSONG_WATCH_DIR` to the `Automatically Add to Music` folder inside it.)

> The first time `addsong` writes there, macOS may ask your terminal for permission
> to access the Music folder. Click **Allow**.

## Usage

```bash
# single track
addsong "https://www.youtube.com/watch?v=..."

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

### Options

| Flag         | Effect                                                       |
|--------------|-------------------------------------------------------------|
| `--playlist` | Import every track in a playlist URL                         |
| `-y`, `--yes`| Don't prompt; accept the scraped/cleaned metadata           |
| `--edit`     | Always prompt to review (even for each track in a playlist)  |
| `--force`    | Import even if the track was imported before                 |
| `-h`,`--help`| Show help                                                   |

Playlists are non-interactive by default; add `--edit` to review each track.

### Settings

Configured with environment variables:

| Variable               | Purpose                            | Default                                |
|------------------------|------------------------------------|----------------------------------------|
| `ADDSONG_WATCH_DIR`    | Apple Music watch folder           | standard macOS path                    |
| `ADDSONG_AUDIO_FORMAT` | Output audio format                | `m4a`                                  |
| `ADDSONG_LEDGER`       | Imported-tracks list (dedup)       | `~/.local/state/addsong/imported.tsv`  |
| `ADDSONG_RETRIES`      | Extra attempts on transient errors | `2`                                    |
| `ADDSONG_RETRY_DELAY`  | Base backoff seconds per attempt   | `3`                                    |

## Notes

- **Metadata** is cleaned automatically: junk like `(Official Video)`, `[4K]`,
  `(Lyrics)` is stripped, and `Artist - Title` is split out (falling back to the
  uploader as artist).
- **Duplicates** are tracked by video ID, so re-runs skip songs already imported.
  Use `--force` to override.
- **Syncing to your phone** is handled by Apple, not this tool. Tracks have to upload
  from your Mac to iCloud (they aren't in Apple's catalog), so keep the Mac open and
  online, and make sure *Sync Library* is on for both devices.
- Some videos (private, region-locked, age-gated) may fail to download. Keep `yt-dlp`
  current (`brew upgrade yt-dlp`) — an outdated version is the usual cause.
