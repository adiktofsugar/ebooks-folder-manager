# The store

efm keeps metadata in a central, content-addressed store. Books themselves stay where they are.

```
$store/                                   # --store, else $EFM_STORE, else $XDG_DATA_HOME/efm/store
  books/xx_<hash>/
    metadata.json                         # normalized, user-facing (Metadata)
    metadata_internal.json                # efm bookkeeping, not shown by ls (InternalMetadata)
    metadata_raw.json                     # what was read, unmodified; null if pymupdf couldn't open the file
    ancestor                              # optional: the hash this version was derived from
    content.json                          # optional: the book's bytes, as a list of chunk ids
  blobs/xx_<chunk hash>                   # one chunk, shared by every version that contains it
```

Stores from before `books/` existed can be moved by hand: `cd $store && mkdir books && mv xx_* books/`. Their old `content` files (whole-book copies) aren't read anymore. If you need one, re-`put_content` it or keep the file.

The store is keyed by hash only. It knows nothing about paths. This is because the store holds all versions of books (except the current one, which is in your folder). For instance, version 1 of a book could be "my_book.acsm", which is just a key that gets sent to Adobe to download the actual epub. That downloaded file will become version 2, and get a new hash. You can revert it to the old version by following its "ancestor" link to the version 1 acsm file. Similarly, if you remove the DRM from the downloaded epub (version 2), then you'll make a new entry (version 3) of the file, probably with the same filepath (my_book.epub).

Again, but as a list:

- run `efm acsm my_folder/my_book.acsm`
- if it doesn't exist, create `$store/books/xx_1` with metadata via `Store.put("xx_1", my_book_entry)`
- stores the file's bytes as `$store/books/xx_1/content.json` + blobs via `Store.put_content("xx_1", "my_folder/my_book.acsm")`
- fulfills the file and returns an epub in the scratch dir
- creates `$store/books/xx_2` with metadata from epub and an `ancestor` of `xx_1` (the acsm entry) via `Store.put()`
- delete the original acsm file, and move the generated my_book.epub content to my_folder/my_book.epub, as the "current version" is now this content entry 

## Commands that replace books

Most commands only read books. Ones that transform a book (`efm acsm` so far; dedrm next) delete the original, which is safe because of the backup in the store.

1. Put the original's content in the store (`Store.put_content`) after making the normal entry (if needed).
2. The work happens in a scratch directory (`/tmp/efm-<command>-XXXX/`, or wherever `$TMPDIR` points). It's deleted on success and kept on failure, with its path logged, so intermediate files can be inspected. It's in the temp dir so dirs kept by repeated failures don't pile up forever; losing one to a reboot just means rerunning the command to reproduce it.
3. Create a new store entry for the result, but with an `ancestor` file with the original's hash. Following `ancestor` links walks back through every version of a book.
4. At this point we delete the original, then move the new entry to the name it should be (which could be the same as the original, or could be something new, depending on the format).

A failure at any step leaves the original where it was. Content is only stored for books that are about to be replaced, so the store doesn't grow by a copy of the whole library.

## Content and chunks

Each version of a book is a new entry. If every version kept a full copy, a one-letter change to a description would cost a whole book. So content is split into chunks with FastCDC (content-defined chunking, as in restic and borg), and each chunk is stored once in `blobs/`, named by its xxh3-128 hash. `content.json` lists a version's chunks in order:

```json
{"schema_version": 1, "size": 1234567, "chunker": {"algo": "fastcdc", "min": 4096, "avg": 16384, "max": 65536}, "chunks": ["xx_...", "..."]}
```

- **Why content-defined.** An edit to an EPUB's OPF changes one zip member and the central directory, but shifts every byte after it. Fixed-size chunks would all change. Content-defined cut points move with the bytes, so only the chunks around the edit are new. PDFs saved incrementally just append bytes. A tool that recompresses every member changes everything, and nothing byte-level helps there. So when efm writes a book itself, it should copy unchanged members raw.
- **Chunk size.** 16 KiB average, small next to restic's ~1 MiB, because books are a few MB and an edit should cost a few chunks. The params are recorded per manifest. Changing them only loses dedup with older versions, never the ability to read them.
- **No compression.** Ebook bytes are already compressed (zip deflate, PDF streams).
- **Flat `blobs/`.** ext4, btrfs and xfs look names up in large directories quickly, so there's no git-style `xx/` fan-out.
- **Writes.** Blobs are written first (atomically, and skipped if they already exist), and `content.json` last. A crash leaves unreferenced blobs, never a manifest pointing at missing ones. The whole stream is hashed while chunking, and must match the entry's hash, which guards against the book changing after it was hashed.
- **Reads.** `Store.get_content(h, out)` streams the chunks into `out`, checking each chunk's hash and the total. Since `out` may already have bytes by the time a check fails, `Store.restore_content(h, file)` goes through a temp file and only replaces `file` once everything verifies. A revert would be `restore_content(entry.ancestor, book_file)`.
- **Garbage.** Nothing deletes entries yet. A future `gc` marks every chunk listed in a `content.json` and deletes the rest of `blobs/`.
- With dedup this cheap, storing content for every version (not just ones about to be replaced) becomes reasonable. It hasn't been decided.

`Store.put_content`/`get_content`/`has_content`/`restore_content` delegate to `ContentStore` (`efm/content_store.py`).

## `efm store`

Other commands take paths, while `efm store` subcommands take hashes:

- `efm store show <hash> [-o file]`: the stored content, to stdout (like `git show <hash>`) or to a file.
- `efm store ancestor <hash> [-a]`: the hash it was derived from, or the whole chain with `-a`.
- `efm store ls [--has-content] [-f line|table|json] [--raw]`: every entry, one per line as hash, title and author.
- `efm store info`: the store's path, which setting chose it (`--store`, `$EFM_STORE`, or the default), and how many books and blobs it holds.

## Hashing

Full-file xxh3-128 (`xxhash`). It doesn't need to be cryptographic, just unique, and xxh3 is about as fast as reading the file. Hashes are prefixed with the algorithm (`xx_`) so a future algorithm can't collide with existing entries.

### Why there's no partial hash

A partial hash (size + first/last N bytes) can only prove two files are *different*, never that they're the *same*. Nothing about a partial match tells you "that's enough". The only way to know is to hash the rest. So the shortcut has to come from somewhere else: the stat cache.

## Stat cache

```
$XDG_CACHE_HOME/efm/stat-cache/<abs book path>/<size>-<mtime_ns>-<ctime_ns>    # contents: xx_<hash>
```

The filesystem is the key-value store. A lookup is a single small file read. On a hit the book isn't opened at all. This trusts that a changed file has a changed size, mtime, or ctime, which is the same assumption `make` and `rsync` rely on. `ctime` catches tools that restore mtime after editing.

- Reads are validated against the hash format. A partial or foreign file is a miss, never a wrong hash. Any filesystem error (missing, is-a-directory, name too long) is also a miss.
- `put` deletes that path's older keys first, so there's one entry per book path.
- Write failures are logged at debug level and ignored. The cache is optional.
- Entries for deleted or moved books linger. `rm -rf ~/.cache/efm/stat-cache` is always safe.
- `--no-stat-cache` bypasses it entirely, which is useful for benchmarking (`--loglevel debug` prints hits, files hashed, and time).

## Schema versions

`metadata.json` and `metadata_internal.json` each carry a `schema_version`, and each version is its own pydantic model in `efm/metadata.py`:

- `MetadataVX` reads only `schema_version`, to pick the model.
- `MetadataV1`, `MetadataV2`, ... are frozen, `extra="forbid"`, with `schema_version: Literal[n]`.
- `Metadata` is an alias for the current version; code outside `metadata.py` only uses the alias.
- `AnyMetadata` is the union of all versions, and `METADATA_MODELS` maps version numbers to models.
- `migrate_metadata(m: AnyMetadata) -> Metadata` is a `match` ending in `assert_never`, so the type checker (ty) fails if a version in the union isn't handled.

`InternalMetadata` follows the same pattern.

Migrations run in memory on every load; files on disk aren't rewritten. A record with an unknown (newer) version, or one that fails validation, raises `InvalidStoreEntryError` instead of being regenerated.

### Raw metadata and re-extraction

`metadata_raw.json` isn't versioned. It holds `pymupdf_fields` (what pymupdf reported: `metadata`, `page_count`, `embfile_names`), plus `epub_fields` or `cbz_fields` when pymupdf reports an EPUB or a zip (CBZ) and that format's own metadata (OPF, `ComicInfo.xml`) could be read. That's where `series` comes from.

`metadata_internal.json` records the `extractor_version` that made the entry. When extraction learns something new, `EXTRACTOR_VERSION` in `efm/metadata.py` is bumped, and `ls`/`find`/`rename` re-extract older entries on their next read (`listing.load_or_create_entry`), keeping `ancestor`. This rewrites the `metadata*.json` files, which is fine while they're purely extracted. Once there are user edits to metadata, those will need to live somewhere re-extraction doesn't touch.

### Adding a version

1. Add `MetadataV2` with `schema_version: Literal[2] = 2`.
2. Add it to `AnyMetadata` and `METADATA_MODELS`.
3. Write `v1_to_v2(m: MetadataV1) -> MetadataV2`. Change the V1 case to `return migrate_metadata(v1_to_v2(m))` and add a `case MetadataV2(): return m`.
4. Point `Metadata` at `MetadataV2`.
5. Update `normalize` (or whatever builds new records) to produce V2.
