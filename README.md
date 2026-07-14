<h3 align="center">addsong</h3>

<p align="center">
  <img src="assets/demo.gif" alt="addsong demo" width="600">
</p>

<p align="center"><b>Paste a link, and the song shows up in Apple Music automatically.</b></p>

`addsong` takes a song name or a YouTube link. It downloads the track, adds the
**title, artist, and cover art**, and drops it into Apple Music. No dragging
files around — making downloading unofficial music seamless.

```bash
addsong "songname"
addsong "https://www.youtube.com/watch?v=..."
```

## Installation

### macOS&nbsp;<img src="assets/macos.svg" height="22" align="absmiddle" style="position: relative; top: -3px;"> 

```bash
brew install ado11231/tap/addsong
```

### Linux&nbsp;<img src="assets/linux.svg" height="22" align="absmiddle" style="position: relative; top: -3px;"> 

```bash
curl -fsSL https://ado11231.github.io/addsong/install.sh | bash
```

### Windows&nbsp;<img src="assets/windows.svg" height="22" align="absmiddle" style="position: relative; top: -3px;"> 

Paste it into **PowerShell**. When it finishes, open a new terminal and run
`addsong` from anywhere — PowerShell, CMD, or any shell:

```powershell
irm https://ado11231.github.io/addsong/install.ps1 | iex
```

Check version to see if installation worked.

```bash
addsong --version
```

## Updating

Re-run the install one-liner above to upgrade to the latest `main`. To pin a
specific version, set `ADDSONG_REF` before running the installer, e.g.
`ADDSONG_REF=v1.0.0`. Homebrew users get updates via `brew upgrade`.

## Your First Song

```bash
addsong "songname"
```

`addsong` shows what it found so you can fix mistakes before it saves:

```
  Review track ♪
  Artist: Artist Name
  Title:  Song Title

  [Enter] Add  ·  [E] Edit  ·  [S] Skip
  ❯
```

Press **Enter** and the song lands in Apple Music a second later.

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
| `addsong forget`               | Forget everything added (so it can be re-added) |



## Flags


| Flag                    | What it does                                           |
| ----------------------- | ------------------------------------------------------ |
| `-y`                    | Don't ask, just add it                                 |
| `--review`              | Always pause to fix the title/artist first             |
| `--reimport`            | Add a song again even if you already have it           |
| `--dry-run`             | Show what would happen, without downloading            |
| `--format FMT`          | Output format: `m4a` (default), `mp3`, `flac`, `opus`… |
| `--quality N`           | Audio quality `0`-`10` (`0` = best, the default)       |
| `--notify`              | Pop a desktop notification as each song imports        |
| `--quiet` / `--verbose` | Show less / more output                                |
| `--help`                | Full list of commands and options                      |


Set environment variables like `ADDSONG_WATCH_DIR` for permanent defaults.

Run `addsong --help` for the full list.

## Download Location

On macOS and Windows they go straight into Apple Music; on Linux they land in
`~/Music/addsong/`. Point them elsewhere with `ADDSONG_WATCH_DIR=/your/folder`.

## Common Errors

- `command not found` — reopen your terminal; if it persists, re-run the [Installation](#installation) step.
- **Nothing shows up** — open the Apple Music app and keep it open while adding (macOS/Windows).
- **A download failed** — update `yt-dlp`, then retry with `--verbose` to see why.