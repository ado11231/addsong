# Features

* Everything addsong does today, what is planned, and what it will never do.
* For anyone checking what addsong can do, or deciding what to build next.
* For how the code works, read [ARCHITECTURE.md](ARCHITECTURE.md).

## Contents

1. [Status](#status)
2. [Adding Songs](#adding-songs)
3. [Song Details](#song-details)
4. [Playlists You Follow](#playlists-you-follow)
5. [Skipping Songs You Have](#skipping-songs-you-have)
6. [Where Songs Go](#where-songs-go)
7. [Output](#output)
8. [Settings](#settings)
9. [The Program](#the-program)
10. [Planned Features](#planned-features)
11. [Never Planned](#never-planned)
12. [Terms](#terms)

## Status

| Status | Meaning |
| --- | --- |
| **Done** | Works in the program, and is tested. |
| **Proposed** | An idea for later. The design may still change. |

## Adding Songs

* Every way of adding a song ends in the same steps: download, tag, and move into Apple Music.

| Feature | What It Does | Status |
| --- | --- | --- |
| Search by name | `addsong "song name"` adds the top YouTube result. No quotes needed. | Done |
| Add a link | `addsong "<link>"` adds one video. | Done |
| Several results | `--results N` adds the top N search results, up to 50. | Done |
| Whole playlist | `--playlist "<link>"` adds every song in a playlist. | Done |
| From a file | `--from list.txt` adds every link in a file, one per line. Blank lines and lines starting with `#` are skipped. `--from -` reads from the keyboard or a pipe. | Done |
| Dry run | `--dry-run` shows what would be added, and downloads nothing. | Done |
| Audio format | `--format` picks `m4a`, `mp3`, `flac`, or `opus`. The default is `m4a`. | Done |
| Audio quality | `--quality` picks 0 to 10. 0 is best, and the default. | Done |
| Retry | Retries a failed download twice, waiting longer each time. Does not retry errors that will never work, such as a private or removed video. | Done |

* Only one of `--from`, `--playlist`, `--results`, or a link can be used at a time.

## Song Details

| Feature | What It Does | Status |
| --- | --- | --- |
| Clean titles | Removes extra words from titles, such as `(Official Video)`, `[4K]`, `(Lyrics)`, and `(feat. X)`. | Done |
| Find the artist | Uses YouTube Music details when they exist. Otherwise splits titles like `Artist - Title`. Otherwise uses the channel name. | Done |
| Tags | Writes the title, artist, album, year, and track number into the file. | Done |
| Cover art | Adds the video thumbnail as the cover. | Done |
| Review | Before downloading one song, shows the artist and title. Press `Enter` to add, `E` to edit, or `S` to skip. | Done |
| Skip the review | `-y` adds without asking. | Done |
| Always review | `--review` asks for every song, even in a playlist. | Done |

### When The Review Shows

| Run | Review |
| --- | --- |
| One song in a terminal | Yes |
| A playlist, a search with `--results`, or `--from` | No, unless `--review` is used |
| With `-y` or `--dry-run` | No |
| Not in a terminal, such as a script | No |

## Playlists You Follow

| Feature | What It Does | Status |
| --- | --- | --- |
| Follow | `addsong subscribe "<link>"` saves a playlist to follow. | Done |
| Sync | `addsong sync` adds any new songs from every playlist you follow. Songs you already have are skipped. | Done |
| List | `addsong list` shows the playlists you follow. | Done |
| Stop following | `addsong unsubscribe "<link>"` removes a playlist. | Done |

* `sync` works with `-y`, `--review`, `--dry-run`, and `--reimport`.

## Skipping Songs You Have

* addsong keeps a list of every song it added, called the history.

| Feature | What It Does | Status |
| --- | --- | --- |
| Skip songs you have | A song in the history is skipped. For YouTube links this is checked before going online. | Done |
| Add again | `--reimport` adds a song even if it is in the history. | Done |
| Forget | `addsong forget` clears the history, so every song can be added again. It asks first. `-y` skips the question. | Done |

## Where Songs Go

* addsong never talks to Apple Music directly. It puts the file in a folder that Apple Music watches, and Apple Music adds it by itself.

| System | Folder |
| --- | --- |
| macOS | `~/Music/Music/Media.localized/Automatically Add to Music.localized` |
| Windows, Apple Music app | `Music\Apple Music\Media\Automatically Add to Apple Music` |
| Windows, iTunes | `Music\iTunes\iTunes Media\Automatically Add to iTunes` |
| WSL | The Windows folders above, found under `/mnt/c` to `/mnt/z` |
| Linux | `~/Music/addsong`. There is no Apple Music, so you add the files to your player yourself. |

* `ADDSONG_WATCH_DIR` replaces the folder on any system.
* If Apple Music is closed, it adds the file the next time it opens.
* If a file with the same name is already there, the new file gets a number added to its name.

## Output

| Feature | What It Does | Status |
| --- | --- | --- |
| Progress bar | Shows download progress in a terminal. `--no-progress` shows a spinner instead. | Done |
| Summary | Ends with how many songs were added, skipped, and failed. | Done |
| Quiet and verbose | `--quiet` shows less. `--verbose` also shows messages from yt-dlp and ffmpeg. | Done |
| No color | `--no-color` or the `NO_COLOR` setting turns color off. Color is also off when not in a terminal. | Done |
| Notifications | `--notify` shows a desktop notification for each song added. Works on macOS and Linux. | Done |

## Settings

* Settings can be environment variables, or lines in `~/.config/addsong/config`, such as `ADDSONG_NOTIFY=1`.
* An environment variable wins over the file. A flag wins over both.
* Only names starting with `ADDSONG_` are read from the file. The file is read as text, never run.

| Setting | What It Changes | Default |
| --- | --- | --- |
| `ADDSONG_WATCH_DIR` | Where songs go | See [Where Songs Go](#where-songs-go) |
| `ADDSONG_AUDIO_FORMAT` | The audio format | `m4a` |
| `ADDSONG_AUDIO_QUALITY` | The audio quality, 0 to 10 | `0` |
| `ADDSONG_RETRIES` | How many times to retry a download | `2` |
| `ADDSONG_RETRY_DELAY` | Seconds to wait before a retry. Grows each time. | `3` |
| `ADDSONG_PROGRESS` | Set to `0` to use the spinner | On |
| `ADDSONG_NOTIFY` | Set to `1` to turn on notifications | Off |
| `ADDSONG_LEDGER` | Where the history file is kept | `~/.local/state/addsong/imported.tsv` |
| `ADDSONG_SUBSCRIPTIONS` | Where the followed playlists are kept | `~/.local/state/addsong/subscribed.tsv` |
| `ADDSONG_CONFIG` | Where the settings file is | `~/.config/addsong/config` |

## The Program

| Feature | What It Does | Status |
| --- | --- | --- |
| Install | `pipx install addsong` on macOS, Windows, and Linux. Needs Python 3.11 or later. | Done |
| Check tools | Before downloading, checks that yt-dlp and ffmpeg are installed and the folder exists, and says how to fix it if not. | Done |
| Shell completion | `--print-completion bash`, `zsh`, or `fish` prints a script that completes commands and flags. | Done |
| Exit code | Ends with 0 when nothing failed, and 1 when any song failed. | Done |
| Help | `--help` lists every command, flag, and example. `--version` prints the version. | Done |
| History | `addsong history` lists every song added, with the date. | Proposed |

## Planned Features

| Area | What It Would Do |
| --- | --- |
| History | `addsong history` lists every song added, with the date. The history file already keeps this. |
| Review on Windows | Show the review, progress bar, and spinner in Windows terminals. Today they are skipped there, and `forget` needs `-y`. |
| Notifications on Windows | Show a notification when a song is added. |
| More formats | Make `best` work in `--format`, and test `aac`, `alac`, `vorbis`, and `wav`. |
| Windows tests | Run the tests on Windows in CI. |

## Never Planned

| Feature | Why |
| --- | --- |
| Signing in to Apple, or using an Apple API | The watched folder needs no account or keys. |
| Controlling the Music app with AppleScript | It breaks with macOS updates, and needs the app open. |
| Editing the Music library file | It can break your library. |
| Downloading videos | addsong is for music only. |
| A background service | addsong runs, adds the songs, and exits. |
| More install methods | PyPI is the only install method, so there is one release to keep current. |

## Terms

| Term | Meaning |
| --- | --- |
| **yt-dlp** | The tool that finds and downloads the audio. |
| **ffmpeg** | The tool that writes the tags into the audio file. |
| **Tags** | Details stored inside a song file, such as the title and artist. |
| **Watched folder** | The "Automatically Add to Music" folder. Apple Music adds anything put there. |
| **History** | The list of songs addsong has added, used to skip songs you have. Also called the ledger. |
| **Subscription** | A playlist you follow with `subscribe`. |
| **pipx** | A tool that installs Python programs in their own space. |
| **WSL** | Windows Subsystem for Linux. Runs Linux inside Windows. |
