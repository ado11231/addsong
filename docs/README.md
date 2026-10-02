# Docs Guide

* Which doc answers which question, and how to write them.
* For anyone reading or changing the addsong docs.

## Contents

1. [The Docs](#the-docs)
2. [Where Changes Go](#where-changes-go)
3. [How To Write](#how-to-write)

## The Docs

| Doc | Answers |
| --- | --- |
| [Project README](../README.md) | What addsong is, and how to install and use it. |
| [FEATURES.md](FEATURES.md) | What addsong does, what is planned, and what it will never do. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the code is organized, and how a song goes from a link to Apple Music. |
| [RELEASE.md](RELEASE.md) | How a new version gets to PyPI. |
| [Wiki](https://github.com/ado11231/addsong/wiki) | Where to find each doc and section. It only links here, so the docs stay in one place. |

## Where Changes Go

| If You | Update |
| --- | --- |
| Add or change a command or a flag | The [Project README](../README.md) and [FEATURES.md](FEATURES.md) |
| Add or change a setting | [FEATURES.md](FEATURES.md#settings) |
| Add or move a file | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Change how a song is downloaded, tagged, or moved | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Change how a release is made | [RELEASE.md](RELEASE.md) |
| Add, rename, or remove a doc or a heading | The wiki sidebar and Home page, so their links still work |

## How To Write

1. Start with a title, then a few bullets on what the doc covers and who it is for, then a numbered Contents list.
2. Use bullets, numbered steps, and tables. No paragraphs.
3. Capitalize every word in headings.
4. No em dashes. No hyphens in ordinary text. Hyphens are fine in code, commands, and file names.
5. Use plain words and short sentences. Explain a term the first time it appears.
6. Keep diagrams small. Put them in the same order as the sections that explain them.
7. Docs describe how things are now. No dates.
8. Never describe planned work as done.
