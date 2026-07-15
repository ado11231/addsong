# Releasing addsong (PyPI)

addsong is published to [PyPI](https://pypi.org/project/addsong/) via the
`.github/workflows/release.yml` GitHub Action, which builds the wheel + sdist
and uploads them using **OIDC trusted publishing** (no API token stored as a
secret). Users then `pipx install addsong` on every OS.

## Prerequisites (one time)

1. The `release.yml` workflow is set up to run on a `v*` tag push and publish
   via `pypa/gh-action-pypi-publish` with `id-token: write`.
2. On PyPI, register the project (first release) and configure the trusted
   publisher:
   - Go to **https://pypi.org/manage/project/addsong/settings/publishing/**.
   - Add a **Pending publisher** (or edit the existing one):
     - PyPI Project Name: `addsong`
     - Owner: `ado11231`
     - Repository name: `apple-music-pipeline`
     - Workflow name: `release.yml`
     - Environment name: `pypi` (matches the workflow's `environment:`)
   - This must be done once *before* the first tagged release, or the upload
     step will fail.

## 1. Bump The Version

The version lives in one place: `__version__` in `src/addsong/__init__.py`.
Hatchling reads it for the wheel/sdist (`dynamic = ["version"]` in
`pyproject.toml`). Bump it (e.g. to `1.1.0`), commit, and push to `main`:

```bash
$EDITOR src/addsong/__init__.py     # set __version__ = "1.1.0"
git add src/addsong/__init__.py
git commit -m "release: 1.1.0"
git push
```

## 2. Tag And Push

The tag must match the version (minus the leading `v`):

```bash
git tag -a v1.1.0 -m "addsong 1.1.0"
git push origin v1.1.0
```

## 3. The Workflow Publishes

Pushing the `v*` tag triggers `release.yml`, which:

1. Checks out the ref at the tag.
2. Builds the wheel and sdist with `python -m build`.
3. Uploads them to PyPI using OIDC trusted publishing (environment `pypi`).

Watch it under **Actions → "Release → PyPI"** on the tag ref. When it's green,
the new version is installable:

```bash
pipx install addsong==1.1.0
addsong --version            # => addsong 1.1.0
```

## Future Releases

1. Bump `__version__` in `src/addsong/__init__.py`, commit, push to `main`.
2. Tag `vX.Y.Z` and push the tag. The workflow does the rest.

## Rollback

PyPI doesn't allow re-uploading the same filename. To pull a broken release,
delete the version from the PyPI project page (file by file); users who pinned
the bad version will need to upgrade past it. To republish fixes, bump the
version (even a patch) and release again.