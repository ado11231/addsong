# Setup Guide

First-time setup for `apple-music-pipeline` on macOS. Follow it once; after that
`addsong <url>` just works.

> **Do Step 3 (the watch-folder test) before writing any script.** It's a 2-minute
> sanity check that confirms the "instant import" actually works on *your* machine.
> Everything else is pointless if this step fails.

---

## Step 1 — Install dependencies

```bash
brew install yt-dlp ffmpeg
```

Verify:

```bash
yt-dlp --version
ffmpeg -version
```

If you don't have Homebrew: https://brew.sh

## Step 2 — Find your Apple Music watch folder

Apple Music auto-imports anything dropped into its watch folder. The usual path is:

```
~/Music/Music/Media.localized/Automatically Add to Music.localized/
```

Check it exists:

```bash
ls ~/Music/Music/Media.localized/ | grep -i "Automatically Add"
```

- If you see `Automatically Add to Music.localized` → you're set, note this path.
- If not, your library may be in a custom location or use a different name. Open
  **Music → Settings → Files** to find your "Music Media folder location," then look
  for an `Automatically Add to Music` folder inside it. Record whatever the real
  path is — the `addsong` script needs to point there.

> The `.localized` suffix is normal; Finder hides it and shows a friendly name.

## Step 3 — Verify auto-import works (the important test)

Don't automate anything until you've confirmed Apple Music actually imports from the
folder.

1. Grab any audio file you already have (an `.m4a` or `.mp3`).
2. Copy it into the watch folder:
   ```bash
   cp "/path/to/some-song.m4a" \
      ~/Music/Music/Media.localized/"Automatically Add to Music.localized"/
   ```
3. Open the **Music** app (it must be running / opened at least once for the watch
   to trigger).
4. Within a few seconds the song should appear in your library, and the file should
   disappear from the watch folder (Apple moves it into the Media library).

✅ **If it imported automatically → the whole pipeline will work. Proceed.**
❌ **If nothing happened** → confirm the path from Step 2, make sure Music is open,
   and that the file is a valid audio file. Resolve this before going further.

## Step 4 — Install the `addsong` command

The `addsong` script lives in the repo root. Install it like this:

1. Place the `addsong` script in a folder on your `PATH`:
   ```bash
   mkdir -p ~/bin
   mv addsong ~/bin/addsong
   chmod +x ~/bin/addsong
   ```
2. Make sure `~/bin` is on your `PATH`. Add this to `~/.zshrc` if needed:
   ```bash
   export PATH="$HOME/bin:$PATH"
   ```
   Then reload:
   ```bash
   source ~/.zshrc
   ```
3. Test:
   ```bash
   addsong --help        # or just run it with a URL once it's built
   ```

## Step 5 — First real run

```bash
addsong "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Expected:
- yt-dlp downloads and converts to `.m4a`
- the tagged file lands in the watch folder
- Apple Music imports it within a couple seconds
- the track shows up in your library with title, artist, and cover art

## Troubleshooting

| Symptom | Likely cause / fix |
|--------|---------------------|
| Song downloads but never appears in Music | Watch-folder path wrong, or Music app not open. Re-do Step 3. |
| Appears but with junk title | Use the interactive review (press `e` to edit artist/title), or re-tag in Music. |
| `yt-dlp: command not found` | Homebrew install didn't finish or `PATH` issue. Re-run Step 1. |
| Missing cover art | Thumbnail embed failed; ensure `ffmpeg` is installed (yt-dlp needs it). |
| Downloads fail on some videos | Age-gated/region-locked content may need cookies — known limitation. |
| Duplicate copies pile up | Dedup tracks imported video IDs in a ledger; re-runs are skipped unless you pass `--force`. |

## Updating the tools

```bash
brew upgrade yt-dlp ffmpeg
```

Keep `yt-dlp` current — YouTube changes often, and an outdated `yt-dlp` is the #1
cause of sudden download failures.
