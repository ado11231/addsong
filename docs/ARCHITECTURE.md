# Architecture

`addsong` is a Python package (installable via pip/pipx) that exposes a single
`addsong` console-script. It has no daemon, no API access, and no dependency on
AppleScript or the Music app's scripting interface. It relies on one behavior
that Apple Music (macOS), the Apple Music preview app (Windows 11), and legacy
iTunes (Windows) all share: each scans a per-library "Automatically Add to ..."
watch folder and imports anything dropped there. On Linux / WSL without a
Windows library, `addsong` falls back to writing tagged files into an output
folder for manual import into any player.

External binaries (invoked as subprocesses, no library imports):

- `yt-dlp` — metadata extraction, audio download, thumbnail embed, flat-playlist
  expansion, YouTube search.
- `ffmpeg` — re-mux/tagging with `-c copy` (preserves embedded artwork).

Platform detection lives in `platform.detect_os()` (`mac` / `win` / `wsl` /
`linux` / `other`); `platform.default_watch_dir()` returns the appropriate
default per OS, and `ADDSONG_WATCH_DIR` always overrides it.

## Module Map (`src/addsong/`)

| Module               | Responsibility                                             |
| -------------------- | ---------------------------------------------------------- |
| `constants.py`        | Audio formats, yt-dlp hard-error regex, exit codes, defaults. |
| `config.py`           | `Config` dataclass + `load_config()` parsing `ADDSONG_*` KEY=VALUE config (env over file, ADDSONG_* keys only). |
| `platform.py`        | `detect_os()` and `default_watch_dir()` per-OS watch folder probing. |
| `meta.py`            | `clean_meta()` (the Unicode-aware title scrubber), `safe_name()`, `id_from_url()`, `parse_meta()` + `TrackMeta`. |
| `ytdlp.py`           | `run_ytdlp()` subprocess wrapper with bounded linear-backoff retry and hard-error classification; stderr-to-file, stdout-to-file-or-progress-callback. |
| `ffmpeg.py`           | `finalize_track()` re-tag with `-c copy`, collision-safe move into the watch folder; ledger/status/notify/callbacks via injected callables. |
| `ledger.py`           | TSV dedup ledger (has/add/clear/count/read_rows).          |
| `subscriptions.py`    | Subscriptions file (add/remove/read_urls/has_subscriptions). |
| `ui.py`              | `rich`-backed console: err/say/banner/status, spinner, progress bar, finish_batch summary, desktop notify. Colors honor `--no-color`/`NO_COLOR`/no-TTY; icons render only when `Console.color_system` is non-None so non-TTY output stays plain-text greppable. |
| `review.py`           | Interactive accept/edit/skip `review_meta()` + `confirm_forget()` over `/dev/tty`. |
| `pipeline.py`        | `Run`/`Flags`, `process_one` (slow/fast paths), `interactive_for`, `run_url_stream`, `builtin_search/playlist/from_file/sync/forget`, `finish_batch`, `preflight`. |
| `completion.py`       | Shell-completion script generation for `--print-completion bash/zsh/fish`; flags/subcommands declared once and rendered per shell. |
| `cli.py`             | `argparse` parser, subcommand peek, mutual-exclusivity rules, `--print-completion`, exit-code dispatch. |

## The Pipeline (Per Track)

`pipeline.process_one(run, url, interactive)` runs one track:

1. **Zero-network dedup.** If `meta.id_from_url()` extracts an 11-char YouTube
   id from the URL and `ledger.has()` already has it, the track is skipped
   without touching the network (`--reimport` overrides).
2. **Slow vs fast path.** Non-interactive, non-dry-run runs take the
   **fast path**: one `yt-dlp --no-simulate --print-to-file` call combines the
   download with metadata capture, saving a round trip. Interactive/dry-run
   runs take the **slow path**: a `yt-dlp --print` metadata read first, so the
   review prompt or the `Would add` line can show without committing a download.
3. **Clean it up.** `clean_meta()` strips junk like `(Official Video)`, `[4K]`,
   and `(feat. X)`. If the title looks like `Artist - Title` it is split;
   otherwise the uploader becomes the artist. Structured YouTube Music metadata
   (track + artist) is used as-is.
4. **Review (interactive runs).** `review.review_meta()` shows the resolved
   artist/title and lets you accept, edit, or skip before any download.
   Playlists are non-interactive unless `--review` is passed.
5. **Duplicate guard (post-metadata).** After metadata is parsed, a second
   `ledger.has()` check covers non-YouTube-URL tracks that had no parseable id
   upfront.
6. **Download + tag.** `ytdlp.run_ytdlp()` retries transient failures with
   linear backoff and bails on hard errors (`YTDLP_HARD_ERRORS`). `ui` shows a
   real progress bar at a TTY, a spinner otherwise. `ffmpeg.finalize_track()`
   writes the chosen title/artist/album/year/track tags with `-c copy`, preserving
   the embedded artwork.
7. **Hand off to Apple Music.** The tagged file is collision-safely moved into
   the watch folder; Apple Music imports it on its own a moment later.
8. **Record + notify.** On success, `ledger.add()` records the import, the UI
   prints `Added artist - title`, and a desktop notification fires if `--notify`.

## Why The Watch Folder

Using the watch folder instead of AppleScript or the Music API means:

- **No credentials.** No Apple ID, API key, or cookies are involved.
- **Fewer moving parts.** Importing is the OS's job; the script just produces a
  correctly tagged file and moves it.
- **Resilience.** If Music is closed when a file is written, it is imported the
  next time Music opens.

## Exit Codes (Per Track)

`process_one()` returns `0` (added), `2` (skipped — duplicate or user skip),
or `1` (failed). The top-level run aggregates these in `finish_batch()` and
exits non-zero (`1`) if any track failed, `0` otherwise. `forget` returns `1`
when it refuses to wipe the ledger without a TTY for confirmation (`-y` skips
the prompt).

## State And Side Effects

- **Ledger:** append-only TSV at `ADDSONG_LEDGER`
  (`~/.local/state/addsong/imported.tsv`), one row per imported track:
  `id<TAB>artist<TAB>title<TAB>YYYY-MM-DDTHH:MM:SS`. This is the source of
  truth for `sync`'s "only new tracks" behavior — there's no per-subscription
  last-seen marker. `forget` removes the file.
- **Subscriptions:** plain-text list of playlist URLs at
  `ADDSONG_SUBSCRIPTIONS` (`~/.local/state/addsong/subscribed.tsv`), one URL per
  line, `#` comments and blanks allowed. Edited only by `subscribe`/
  `unsubscribe`; read by `list`/`sync`.
- **Config file:** `~/.config/addsong/config` (`ADDSONG_CONFIG`), KEY=VALUE
  pairs accepted only for `ADDSONG_*` keys (parsed, not executed — arbitrary
  code can't run). Environment variables override the file.
- **Staging:** each download uses a `tempfile.mkdtemp()` directory that is
  removed whether the track succeeds or fails.
- **Output:** exactly one tagged audio file moved into `ADDSONG_WATCH_DIR` per
  successful track. On-disk state-file formats are stable across releases, so
  existing ledgers and subscription lists survive an upgrade.