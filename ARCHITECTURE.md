# Architecture

`addsong` is a single Bash script. It has no daemon, no API access, and no
dependency on AppleScript or the Music app's scripting interface. It relies on
one behavior that Apple Music (macOS), the Apple Music preview app (Windows 11),
and legacy iTunes (Windows) all share: each scans a per-library "Automatically
Add to ..." watch folder and imports anything dropped there. On Linux / WSL
without a Windows library, `addsong` falls back to writing tagged files into an
output folder for manual import into any player.

Platform detection lives in `detect_os()` (`mac` / `win` / `wsl` / `linux` /
`other`); `default_watch_dir()` returns the appropriate default per OS, and
`ADDSONG_WATCH_DIR` always overrides it.

## The Pipeline (Per Track)

1. **Read metadata, no download.** `yt-dlp --print` fetches the video id, title,
   and uploader without downloading anything.
2. **Clean it up.** `clean_meta()` strips junk like `(Official Video)`, `[4K]`,
   and `(feat. X)`. If the title looks like `Artist - Title` it is split;
   otherwise the uploader becomes the artist.
3. **Review (interactive runs).** For a single track at a terminal, the resolved
   artist/title are shown so you can accept, edit, or skip before any download.
   Playlists are non-interactive unless `--edit` is passed.
4. **Duplicate guard.** Each imported track's video id is recorded in a ledger
   (`ADDSONG_LEDGER`). Already-seen ids are skipped unless `--force` is given.
5. **Download + tag.** `yt-dlp` extracts the audio and embeds the thumbnail;
   `ffmpeg` writes the chosen title/artist tags (copying streams, so the embedded
   artwork is preserved). At a terminal a spinner shows progress while each step
   runs.
6. **Hand off to Apple Music.** The tagged file is moved into the watch folder.
   Apple Music imports it on its own a moment later.

## Why The Watch Folder

Using the watch folder instead of AppleScript or the Music API means:

- **No credentials.** No Apple ID, API key, or cookies are involved.
- **Fewer moving parts.** Importing is the OS's job; the script just produces a
  correctly tagged file and moves it.
- **Resilience.** If Music is closed when a file is written, it is imported the
  next time Music opens.

## Key Components In The Script

| Function                                                 | Responsibility                                               |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| `detect_os()`                                            | Return `mac`/`win`/`wsl`/`linux`/`other` from `$OSTYPE`.      |
| `default_watch_dir()`                                    | Default watch/output folder per OS (probes Windows layouts). |
| `clean_meta()`                                           | Normalize a metadata string (strip junk, collapse spaces).   |
| `safe_name()`                                            | Make a string safe to use as a filename.                     |
| `ledger_has()` / `ledger_add()`                          | Duplicate detection by video id.                             |
| `subs_add()`/`subs_remove()`/`subs_list()`/`subs_sync()` | Subscribed-playlist management and sync.                     |
| `run_ytdlp()`                                            | Run `yt-dlp` with bounded retry on transient (network) errors. |
| `with_spinner()`                                         | Show a progress spinner while a step runs (terminal only).   |
| `setup_colors()`                                         | Enable colored output when writing to a terminal.            |
| `review_meta()`                                          | Interactive accept/edit/skip prompt (reads `/dev/tty`).      |
| `process_one()`                                          | Run the full pipeline for one URL.                           |

## Exit Codes (Per Track)

`process_one()` returns `0` (added), `2` (skipped — duplicate or user skip), or
`1` (failed). The top-level run aggregates these into the end-of-run summary and
exits non-zero if any track failed.

## State And Side Effects

- **Ledger:** append-only TSV at `ADDSONG_LEDGER`
  (`~/.local/state/addsong/imported.tsv`), one row per imported track. The ledger
  is also the source of truth for `sync`'s "only new tracks" behavior — there's no
  per-subscription last-seen marker.
- **Subscriptions:** plain-text list of playlist URLs at `ADDSONG_SUBSCRIPTIONS`
  (`~/.local/state/addsong/subscribed.tsv`), one URL per line, `#` comments
  allowed. Edited only by `subscribe`/`unsubscribe`; read by `list`/`sync`.
- **Staging:** each download uses a `mktemp -d` directory that is removed whether
  the track succeeds or fails.
- **Output:** exactly one tagged audio file moved into `ADDSONG_WATCH_DIR`.
