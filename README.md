<h3 align="center">addsong</h3>

<p align="center"><b>Paste a link, and the song shows up in Apple Music automatically.</b></p>

<p align="center">
  <a href="#macos"><img src="assets/macos.svg" height="48" alt="macOS"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#windows"><img src="assets/windows.svg" height="48" alt="Windows"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="#linux"><img src="assets/linux.svg" height="48" alt="Linux"></a>
</p>

```bash
addsong "https://www.youtube.com/watch?v=..."
```

That one command grabs the song, adds the **title, artist, and cover art**, and
hands it to Apple Music. The song appears in your library a second later — no
dragging files around.

Don't have a link? Just type the song's name:

```bash
addsong "songname"
```

**Note:** Songs come from YouTube (and other sites). Only download what you have
the right to.

### Install

One command for your OS installs `addsong` **and** the two free tools it needs
(`yt-dlp` and `ffmpeg`). Then open a new terminal and run `addsong --version`.

**macOS** (Homebrew):

```bash
brew install ado11231/tap/addsong
```

**Linux / WSL** (paste into a terminal):

```bash
curl -fsSL https://raw.githubusercontent.com/ado11231/apple-music-pipeline/main/install.sh | bash
```

**Windows** (paste into **PowerShell**):

```powershell
irm https://raw.githubusercontent.com/ado11231/apple-music-pipeline/main/install.ps1 | iex
```

<details>
<summary>Prefer to install by hand? (or no installer for your setup)</summary>

**1. Download `addsong`.** Use the green **Code** button near the top of this
page → **Download ZIP**, then unzip it.

**2. Get the two free tools it uses** — `yt-dlp` (downloads songs) and `ffmpeg`
(converts them):

```bash
choco install yt-dlp ffmpeg         # Windows (run inside Git Bash or WSL)
sudo apt install yt-dlp ffmpeg      # Debian / Ubuntu
sudo pacman -S yt-dlp ffmpeg        # Arch
```

**3. Put `addsong` where your terminal can find it:**

```bash
mkdir -p ~/bin && mv addsong ~/bin/ && chmod +x ~/bin/addsong
```

**Got `command not found`?** Run this once, reopen your terminal, and try again:

```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc   # use ~/.zshrc on a Mac
```

</details>

### Add Your First Song

Type any song's name — no link needed:

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

### Where Your Songs Go

`addsong` saves songs where your music app imports them, and finds that spot on
its own. **You only need this section if a song doesn't show up** — plus the
one-time notes for Windows and Linux.

#### <img src="assets/macos.svg" height="18" align="absmiddle">&nbsp;macOS

Songs go here, and Apple Music imports them on its own:

```
~/Music/Music/Media.localized/Automatically Add to Music.localized/
```

If nothing shows up, your library may live elsewhere. Find it under
**Music → Settings → Files**, then tell `addsong` where it is:

```bash
export ADDSONG_WATCH_DIR="/path/to/Automatically Add to Music.localized"
```

**Note:** The first time it saves a song, macOS may ask for permission to use
the Music folder. Click **Allow**.

#### <img src="assets/windows.svg" height="18" align="absmiddle">&nbsp;Windows

You'll run `addsong` inside **Git Bash** or **WSL**. **Open the Apple Music app
(or iTunes) once** so it creates your library — then `addsong` can find it.

**Tip:** Keep the default `.m4a` format. Older iTunes can't play `.flac` and
quietly skips those files.

If your library is on another drive, point at it directly:

```bash
export ADDSONG_WATCH_DIR="D:/iTunes/iTunes Media/Automatically Add to iTunes"
```

#### <img src="assets/linux.svg" height="18" align="absmiddle">&nbsp;Linux

There's no Apple Music on Linux, so songs are saved to a folder instead:

```
~/Music/addsong/
```

`addsong` makes this folder and prints where it is. Add the files to any music
player you like. To use a different folder:

```bash
export ADDSONG_WATCH_DIR="/srv/music/inbox"
```

### More Ways To Add Songs

```bash
# paste a link instead of a name
addsong "https://www.youtube.com/watch?v=..."

# see the top 3 matches and choose
addsong --search 3 "80s disco mix"

# add a whole playlist at once
addsong --playlist "https://www.youtube.com/playlist?list=..."
```

#### Follow A Playlist

Subscribe once, then grab new songs whenever you want — it skips anything you
already have:

```bash
addsong subscribe "https://www.youtube.com/playlist?list=PL..."   # follow it
addsong list                                                      # see your list
addsong sync                                                      # grab new songs
```

Stop following with `addsong unsubscribe "<link>"`.

#### Start Over

`addsong` remembers what it has already imported so it never adds the same song
twice. To wipe that memory — so the next add or `sync` treats every song as new
again — clear the ledger:

```bash
addsong clear-ledger        # asks you to confirm first
addsong clear-ledger -y     # skip the confirmation
```

To re-add just one song you already have, use `--force` instead.

### All The Options

The ones you'll reach for most:

| Flag          | What it does                                    |
| ------------- | ----------------------------------------------- |
| `--search N`  | Show the top N matches and let you pick (1–50). |
| `--playlist`  | Add every song in a playlist.                   |
| `--from FILE` | Add every link in a file, one per line.         |
| `-y`          | Skip the confirm prompt and just add it.        |
| `--edit`      | Always let you fix the title first.             |

And a few for when you need them:

| Flag         | What it does                                   |
| ------------ | ---------------------------------------------- |
| `--force`    | Add a song again even if you already have it.  |
| `--dry-run`  | Preview what would happen — downloads nothing. |
| `--no-progress` | Use the spinner instead of the download bar. |
| `--verbose`  | Show the full error when something breaks.     |
| `--quiet`    | Show only errors, nothing else.                |
| `--no-color` | Turn off colored text.                         |
| `--help`     | List every command and option.                 |
| `--version`  | Print the installed version and exit.          |

Want to set something permanently? A few defaults live in environment variables —
the main one is `ADDSONG_WATCH_DIR` (where songs are saved). Run `addsong --help`
for the full list.

### When Something Goes Wrong

- **`command not found: yt-dlp` (or `ffmpeg`).** You're missing the two tools —
  install them (step 2 of [Install](#install)).
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

### For Developers

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
