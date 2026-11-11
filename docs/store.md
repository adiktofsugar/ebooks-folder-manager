# The store

efm keeps metadata in a central, content-addressed store. Books themselves stay where they are.

```
$store/                                   # --store, else $EFM_STORE, else $XDG_DATA_HOME/efm/store
  xx_<hash>/
    metadata.json                         # normalized, user-facing (Metadata)
    metadata_internal.json                # efm bookkeeping, not shown by ls (InternalMetadata)
    metadata_raw.json                     # what pymupdf reported, unmodified; null if it couldn't open the file
    ancestor                              # optional: the hash this version was derived from
    content                               # optional: a copy of the book's bytes
```

The store is keyed by hash only. It knows nothing about paths. This is because the store holds all versions of books (except the current one, which is in your folder). For instance, version 1 of a book could be "my_book.acsm", which is just a key that gets sent to Adobe to download the actual epub. That downloaded file will become version 2, and get a new hash. You can revert it to the old version by following its "ancestor" link to the version 1 acsm file. Similarly, if you remove the DRM from the downloaded epub (version 2), then you'll make a new entry (version 3) of the file, probably with the same filepath (my_book.epub).

Again, but as a list:

- run `efm acsm my_folder/my_book.acsm`
- if it doesn't exist, create `$store/xx_1` with metadata via `Store.put("xx_1", my_book_entry)`
- copies file to `$store/xx_1/content` via `Store.put_content("xx_1", "my_folder/my_book.acsm")`
- fulfills the file and returns an epub in the scratch dir
- creates `$store/xx_2` with metadata from epub and an `ancestor` of `xx_1` (the acsm entry) via `Store.put()`
- delete the original acsm file, and move the generated my_book.epub content to my_folder/my_book.epub, as the "current version" is now this content entry 

## Commands that replace books

Most commands only read books. Ones that transform a book (`efm acsm` so far; dedrm next) delete the original, which is safe because of the backup in the store.

1. Copy the original to the store (`$store/xx_$hash/content`) after making the normal entry (if needed).
2. The work happens in a scratch directory (`/tmp/efm-<command>-XXXX/`, or wherever `$TMPDIR` points). It's deleted on success and kept on failure, with its path logged, so intermediate files can be inspected. It's in the temp dir so dirs kept by repeated failures don't pile up forever; losing one to a reboot just means rerunning the command to reproduce it.
3. Create a new store entry for the result, but with an `ancestor` file with the original's hash. Following `ancestor` links walks back through every version of a book.
4. At this point we delete the original, then move the new entry to the name it should be (which could be the same as the original, or could be something new, depending on the format).

A failure at any step leaves the original where it was. `content` is only written for books that are about to be replaced, so the store doesn't grow by a copy of the whole library.

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

Migrations run in memory on every load; files on disk aren't rewritten. A record with an unknown (newer) version, or one that fails validation, raises `InvalidStoreEntryError` instead of being regenerated, so hand-edited records are never clobbered.

### Adding a version

1. Add `MetadataV2` with `schema_version: Literal[2] = 2`.
2. Add it to `AnyMetadata` and `METADATA_MODELS`.
3. Write `v1_to_v2(m: MetadataV1) -> MetadataV2`. Change the V1 case to `return migrate_metadata(v1_to_v2(m))` and add a `case MetadataV2(): return m`.
4. Point `Metadata` at `MetadataV2`.
5. Update `normalize` (or whatever builds new records) to produce V2.
