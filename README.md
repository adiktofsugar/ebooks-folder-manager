I'm tired of calibre. All I want is to add minimal metadata to my books and keep them in a folder.

Rewriting the books all the time is not a great idea, though, because sometimes things go wrong, and when that happens, your books get destroyed. So, instead, efm leaves your books where they are and keeps metadata in a separate store, keyed by a hash of each book's contents.

```bash
efm ls ~/ebooks              # table of books with title, author, and other metadata
efm ls ~/ebooks -f json      # same, as JSON
efm ls ~/ebooks --raw        # what pymupdf reported, unnormalized
```

The store lives in `~/.local/share/efm/store` (override with `--store` or `$EFM_STORE`):

- store
  - xx_3f2a….
    - metadata.json
    - metadata_internal.json
    - metadata_raw.json

Because entries are keyed by content, a book that's renamed or moved keeps its metadata, and an edited book gets a new entry rather than overwriting the old one. See [docs/store.md](docs/store.md) for details.

Actions like DRM removal and renaming will be separate, manually-run commands (`efm dedrm <file>`, `efm rename <file>`, ...).

# Known issues / Future features

## Multiple formats

Initially, this isn't supported. We'll list each format as a different book, like:

- Where the wild things are (epub)
- Where the wild things are (pdf)

This can, however, get annoying if you wanted to centralize the data. So I think the metadata will eventually contain an "alias" or "target" property that redirects you to a different doc for the info. For example:

```yaml
file: sha123.epub
title: Where the wild things are
year: 1990
description: null
```

```yaml
file: sha123.pdf
alias: sha123.epub
```

I'm not sure how you'd set this up though...hm. Maybe a config file? You'll need a config file for credentials anyway so that makes sense. The site can write to it to save preferences and all that.

## Sync to device

ebooks generally mount as a drive when connected to your computer, and then you can drag them over. The "sync to disk" option should be all you need to sync it to your mounted ebook. You could also copy the "books" directory, but then you'd have weird filenames.

## Books that have more than one output file

Apparently "topaz" books have an svg zip output. I guess metadata can have an "auxiliary_files" key or something?
