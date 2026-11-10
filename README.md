I'm tired of calibre. All I want is to add minimal metadata to my books and keep them in a folder.

efm (Ebooks Folder Manager) is a CLI for managing a single folder of ebooks. There's no library database to import into and no app to keep open: you point it at your folder and it tells you what's there.

Rewriting the books all the time is not a great idea, though, because sometimes things go wrong, and when that happens, your books get destroyed. So, instead, efm leaves your books where they are and keeps metadata in a separate store, keyed by a hash of each book's contents.

# Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git submodule update --init   # adl/ and DeDRM_tools/
uv sync
uv run efm --help
```

# Usage

```bash
efm ls ~/ebooks                      # books directly in ~/ebooks: one "file<TAB>title<TAB>author" line each
efm ls ~/ebooks/*.epub               # just these files
efm ls ~/ebooks -f table             # table with all the metadata
efm ls ~/ebooks -f json              # same, as JSON
efm ls ~/ebooks --raw -f table       # what pymupdf reported, unnormalized

efm find ~/ebooks                    # every book under ~/ebooks, recursively
efm find ~/ebooks 'cats.+epub'       # only paths matching a glob, regex, or substring (! to exclude)
efm find ~/ebooks --author pratchett # metadata filters: --title, --author, --book-format,
efm find ~/ebooks --missing title    #   --encrypted/--no-encrypted, --missing title|author
efm find ~/ebooks --encrypted | wc -l # the default output pipes cleanly
```

Metadata is extracted with PyMuPDF, so anything it can open works: EPUB, PDF, MOBI, FB2, CBZ, XPS, SVG, TXT.

`efm setup` is a menu of DRM key extraction and decryption tools (Adobe, Kindle, Nook), built on [DeDRM_tools](https://github.com/noDRM/DeDRM_tools). Run `efm setup --help` to list them, or `efm setup <tool>` to run one directly. On Linux, getting the Adobe key takes some Wine setup; see [docs/adobe-digital-editions-key.md](docs/adobe-digital-editions-key.md).

`efm acsm <file.acsm ...>` downloads the book an Adobe `.acsm` token stands for and puts it in the token's place (`book.acsm` becomes `book.epub`). It needs `adobe_user` and `adobe_password` in an `efm.toml` in or above the token's directory. The token is kept in the store, so nothing is lost. The downloaded book usually still has DRM.

# The store

The store lives in `~/.local/share/efm/store` (override with `--store` or `$EFM_STORE`):

- store
  - xx_3f2a….
    - metadata.json
    - metadata_internal.json
    - metadata_raw.json
    - ancestor (if this version was made from another, e.g. by `efm acsm`)
    - content (a copy of a book that a command replaced)

Because entries are keyed by content, a book that's renamed or moved keeps its metadata, and an edited book gets a new entry rather than overwriting the old one. A stat cache in `~/.cache/efm` means unchanged files aren't re-hashed on every run. See [docs/store.md](docs/store.md) for details.

# Planned

Other actions like DRM removal and renaming will be separate, manually-run commands like `efm acsm` (`efm dedrm <file>`, `efm rename <file>`, ...). The code for them exists in `efm/action.py` but isn't wired up to subcommands yet.

There's no daemon or file watcher. Every command is meant to be safe to re-run, so if you want something to happen automatically, put it on a cron (see [docs/watch.md](docs/watch.md)).

## Multiple formats

Initially, this isn't supported. Each format is listed as a different book, like:

- Where the wild things are (epub)
- Where the wild things are (pdf)

This can get annoying if you want to centralize the data, so the metadata will probably eventually get an "alias" property that points at another entry for the info. For example:

```yaml
# xx_aaa… (the epub)
title: Where the wild things are
year: 1990
```

```yaml
# xx_bbb… (the pdf)
alias: xx_aaa…
```

I'm not sure how you'd set that up yet. Maybe a command, maybe the config file (which you need for DRM keys anyway).

## Books that have more than one output file

Apparently "topaz" books have an svg zip output. Metadata could have an "auxiliary_files" key or something.
