# The store

efm keeps metadata in a central, content-addressed store. Books themselves stay where they are.

```
$store/                                   # --store, else $EFM_STORE, else $XDG_DATA_HOME/efm/store
  xx_<hash>/
    metadata.json                         # normalized, user-facing (Metadata)
    metadata_internal.json                # efm bookkeeping, not shown by ls (InternalMetadata)
    metadata_raw.json                     # what pymupdf reported, unmodified; null if it couldn't open the file
```

The store is keyed by hash only. It knows nothing about paths. Going from a file to a hash
(`Store.hash_file`) is a separate step from reading an entry (`Store.load`), because "this file on
disk" and "this version of a book" are different things. A path's contents change; a hash's never do.

Each json file is written atomically (temp file + `os.replace`). `metadata.json` is written last, and
`load` only treats an entry as present if it exists, so an interrupted `put` is just redone next time.

## Hashing

Full-file xxh3-128 (`xxhash`). It doesn't need to be cryptographic, just unique, and xxh3 is about as
fast as reading the file. Hashes are prefixed with the algorithm (`xx_`) so a future algorithm can't
collide with existing entries.

### Why there's no partial hash

A partial hash (size + first/last N bytes) can only prove two files are *different*, never that
they're the *same*. Nothing about a partial match tells you "that's enough". The only way to know is to
hash the rest. So the shortcut has to come from somewhere else: the stat cache.

## Stat cache

```
$XDG_CACHE_HOME/efm/stat-cache/<abs book path>/<size>-<mtime_ns>-<ctime_ns>    # contents: xx_<hash>
```

The filesystem is the key-value store. A lookup is a single small file read. On a hit the book isn't
opened at all. This trusts that a changed file has a changed size, mtime, or ctime, which is the same
assumption `make` and `rsync` rely on. `ctime` catches tools that restore mtime after editing.

- Reads are validated against the hash format. A partial or foreign file is a miss, never a wrong hash.
  Any filesystem error (missing, is-a-directory, name too long) is also a miss.
- `put` deletes that path's older keys first, so there's one entry per book path.
- Write failures are logged at debug level and ignored. The cache is optional.
- Entries for deleted or moved books linger. `rm -rf ~/.cache/efm/stat-cache` is always safe.
- `--no-stat-cache` bypasses it entirely, which is useful for benchmarking (`--loglevel debug` prints
  hits, files hashed, and time).

## Schema versions

`metadata.json` and `metadata_internal.json` each carry a `schema_version`, and each version is its own
pydantic model in `efm/metadata.py`:

- `MetadataVX` reads only `schema_version`, to pick the model.
- `MetadataV1`, `MetadataV2`, ... are frozen, `extra="forbid"`, with `schema_version: Literal[n]`.
- `Metadata` is an alias for the current version; code outside `metadata.py` only uses the alias.
- `AnyMetadata` is the union of all versions, and `METADATA_MODELS` maps version numbers to models.
- `migrate_metadata(m: AnyMetadata) -> Metadata` is a `match` ending in `assert_never`, so pyright
  fails if a version in the union isn't handled.

`InternalMetadata` follows the same pattern.

Migrations run in memory on every load; files on disk aren't rewritten. A record with an unknown
(newer) version, or one that fails validation, raises `InvalidStoreEntryError` instead of being
regenerated, so hand-edited records are never clobbered.

### Adding a version

1. Add `MetadataV2` with `schema_version: Literal[2] = 2`.
2. Add it to `AnyMetadata` and `METADATA_MODELS`.
3. Write `v1_to_v2(m: MetadataV1) -> MetadataV2`. Change the V1 case to
   `return migrate_metadata(v1_to_v2(m))` and add a `case MetadataV2(): return m`.
4. Point `Metadata` at `MetadataV2`.
5. Update `normalize` (or whatever builds new records) to produce V2.
