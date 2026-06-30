# Releasing addsong + Publishing The Homebrew Tap

The main repo is already pushed to https://github.com/ado11231/apple-music-pipeline.

## 1. Tag And Push The Release

The version in the script (`VERSION` in `addsong`) and the tag must match.
It is currently `1.4.0`.

```bash
git tag -a v1.4.0 -m "addsong 1.4.0"
git push origin v1.4.0
```

GitHub now serves a source tarball at:

```
https://github.com/ado11231/apple-music-pipeline/archive/refs/tags/v1.4.0.tar.gz
```

## 2. Compute The Tarball Checksum

```bash
curl -sL https://github.com/ado11231/apple-music-pipeline/archive/refs/tags/v1.4.0.tar.gz \
  | shasum -a 256
```

Copy the 64-character hash.

## 3. Create Your Tap Repo (One Time, Reusable For Every Future Tool)

Create an empty repo named exactly **`homebrew-tap`** on GitHub (no README, no
.gitignore), then clone it and add the formula:

```bash
git clone https://github.com/ado11231/homebrew-tap.git ~/homebrew-tap
mkdir -p ~/homebrew-tap/Formula
cp Formula/addsong.rb ~/homebrew-tap/Formula/addsong.rb
```

## 4. Fill In The sha256

In `~/homebrew-tap/Formula/addsong.rb`, replace the placeholder sha256 with the
hash from step 2:

```bash
sed -i 's/0000000000000000000000000000000000000000000000000000000000000000/PASTE_SHA256_HERE/' ~/homebrew-tap/Formula/addsong.rb
```

Commit and push:

```bash
cd ~/homebrew-tap
git add Formula/addsong.rb
git commit -m "addsong 1.4.0"
git push
```

## 5. Test The Install

```bash
brew install ado11231/tap/addsong
addsong --version            # => addsong 1.4.0
```

Optionally audit the formula before publishing:

```bash
brew audit --new --formula ado11231/tap/addsong
brew test addsong
```

## Future Releases

1. Bump `VERSION` in `addsong`, commit and push.
2. Tag `vX.Y.Z`, push the tag.
3. Recompute the sha256 (step 2) and update `url` + `sha256` in the tap's
   `Formula/addsong.rb`, then push the tap.

## The Linux / Windows Installers

`install.sh` (Linux/WSL) and `install.ps1` (Windows) download `addsong` straight
from the **`main`** branch, so a normal `git push` to `main` is all it takes for
new users to get the latest script — no tag or checksum step like the Homebrew
tap needs. To pin an installer to a specific ref instead, users can set
`ADDSONG_REF` (e.g. `ADDSONG_REF=v1.4.0`) before running it.

## Adding More Tools To The Same Tap

Drop another `Formula/<tool>.rb` into the same `homebrew-tap` repo. Users get it
with `brew install ado11231/tap/<tool>` — no new tap needed.
