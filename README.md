<h3 align="center">addsong</h3>

<p align="center"><b>Paste a link, and the song shows up in Apple Music automatically.</b></p>

<p align="center">
  <a href="#macos"><img src="assets/macos.svg" height="48" alt="macOS"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#windows"><img src="assets/windows.svg" height="48" alt="Windows"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#linux"><img src="assets/linux.svg" height="48" alt="Linux"></a>
</p>

That one command grabs the song, adds the **title, artist, and cover art**, and
hands it to Apple Music. The song appears in your library a second later; no
dragging files around.

```bash
addsong "https://www.youtube.com/watch?v=..."
```

Don't have a link? Just type the song's name:

```bash
addsong "songname"
```

## Install

One command for your OS installs `addsong` **and** the two free tools it needs
(`yt-dlp` and `ffmpeg`). Then open a new terminal and run `addsong --version`.

### <img src="assets/macos.svg" height="18" align="absmiddle">&nbsp;macOS (Homebrew)

```bash
brew install ado11231/tap/addsong
```

### <img src="assets/linux.svg" height="18" align="absmiddle">&nbsp;Linux / WSL

```bash
curl -fsSL https://raw.githubusercontent.com/ado11231/apple-music-pipeline/main/install.sh | bash
```

### <img src="assets/windows.svg" height="18" align="absmiddle">&nbsp;Windows

Paste into **PowerShell**:

```powershell
irm https://raw.githubusercontent.com/ado11231/apple-music-pipeline/main/install.ps1 | iex
```

## Add Your First Song

```bash
addsong "songname"
```

`addsong` finds it and shows what it got, so you can catch any mistakes:

```
  Review track ♪
  Artist: Artist Name
  Title:  Song Title

  [Enter] Add  ·  [E] Edit  ·  [S] Skip
  ❯
```

Press **Enter** and it lands in Apple Music. That's the whole thing.

## Where Your Songs Go

`addsong` picks the folder for you. You only need this if a song doesn't show up.

### <img src="assets/macos.svg" height="18" align="absmiddle">&nbsp;macOS

Apple Music imports from:

`~/Music/Music/Media.localized/Automatically Add to Music.localized/`

If nothing appears, check **Music → Settings → Files**. macOS may ask for folder
access the first time — click **Allow**.

### <img src="assets/windows.svg" height="18" align="absmiddle">&nbsp;Windows

Run `addsong` in **Git Bash** or **WSL**. Open **Apple Music** (or iTunes) once
so it creates the import folder. Use the default `.m4a` format — older iTunes skips
`.flac`.

### <img src="assets/linux.svg" height="18" align="absmiddle">&nbsp;Linux

No Apple Music on Linux. Files go to `~/Music/addsong/` for you to import
manually.

Wrong folder? Point `addsong` anywhere:

```bash
export ADDSONG_WATCH_DIR="/path/to/your/folder"
```

## More Ways To Add Songs

```bash
# paste a link instead of a name
addsong "https://www.youtube.com/watch?v=..."

# see the top 3 matches and choose
addsong --search 3 "80s disco mix"

# add a whole playlist at once
addsong --playlist "https://www.youtube.com/playlist?list=..."
```

### Follow A Playlist

Subscribe once, then grab new songs whenever you want — it skips anything you
already have:

```bash
addsong subscribe "https://www.youtube.com/playlist?list=PL..."   # follow it
addsong list                                                      # see your list
addsong sync                                                      # grab new songs
```

Stop following with `addsong unsubscribe "<link>"`.

### Start Over

`addsong` remembers what it has already imported so it never adds the same song
twice. To wipe that memory — so the next add or `sync` treats every song as new
again — clear the ledger:

```bash
addsong clear-ledger        # asks you to confirm first
addsong clear-ledger -y     # skip the confirmation
```

To re-add just one song you already have, use `--force` instead.

## All The Options

The ones you'll reach for most:

- `--search N` — Show the top N matches and let you pick (1–50).
- `--playlist` — Add every song in a playlist.
- `--from FILE` — Add every link in a file, one per line.
- `-y` — Skip the confirm prompt and just add it.
- `--edit` — Always let you fix the title first.

And a few for when you need them:

- `--force` — Add a song again even if you already have it.
- `--dry-run` — Preview what would happen; downloads nothing.
- `--format FMT` — Output format (e.g. `mp3`, `flac`, `opus`); default `m4a`.
- `--quality N` — Audio quality `0`–`10`, where `0` is best (default `0`).
- `--notify` — Pop a desktop notification as each song imports.
- `--no-progress` — Use the spinner instead of the download bar.
- `--verbose` — Show the full error when something breaks.
- `--quiet` — Show only errors, nothing else.
- `--no-color` — Turn off colored text.
- `--help` — List every command and option.
- `--version` — Print the installed version and exit.

Want to set something permanently? A few defaults live in environment variables —
the main one is `ADDSONG_WATCH_DIR` (where songs are saved). Run `addsong --help`
for the full list.

## Tab Completion

Tab-complete subcommands and flags in your shell. The Homebrew install wires this
up automatically. Otherwise, point your shell at the scripts in
[`completions/`](completions):

**bash** — add to your `~/.bashrc`:

```bash
source /path/to/addsong/completions/addsong.bash
```

**zsh** — put `_addsong` on your `fpath` and enable completion in `~/.zshrc`:

```zsh
fpath=(/path/to/addsong/completions $fpath)
autoload -U compinit && compinit
```

Open a new terminal, then type `addsong ` and press **Tab**.

## When Something Goes Wrong

- **`command not found: yt-dlp` (or `ffmpeg`).** You're missing the two tools —
  re-run [Install](#install) for your OS.
- **A song wouldn't download.** It may be private or blocked in your country.
  More often `yt-dlp` is just out of date — update it
  (`brew upgrade yt-dlp` / `choco upgrade yt-dlp` / `sudo pacman -Syu yt-dlp`),
  then add `--verbose` to see the real error.
- **The song never appears (Mac/Windows).** Open the Apple Music app at least
  once so it exists, and keep it open while you add songs.
- **It downloaded but isn't on my phone.** That part is Apple's job — turn on
  **Sync Library** on every device and keep your computer on and online.
- **It grabbed the wrong version.** A name search takes YouTube's top hit, which
  isn't always the real one — use `--edit` to fix it, or `--dry-run` to preview
  before adding.

## For Developers

`addsong` is one self-contained Bash script — its functions can be sourced and
tested without touching the network. Before opening a pull request, run the same
two checks that CI does:

```bash
brew install shellcheck bats-core   # one-time
shellcheck addsong install.sh       # lint the scripts
bats test/                          # run the tests
```

**Learn more:** [how it works](ARCHITECTURE.md) ·
[making a release](RELEASE.md) ·
[license](LICENSE)
