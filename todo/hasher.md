# Move hashing out of the store

`Store.hash_file` and `Store.hash_contents` never touch the store's directory. They only use the stat cache and the hash counters, so having them on `Store` is confusing, and it's the only reason `hash_file` and `load` need to be explained as separate steps.

## Plan

- Move them to a `Hasher` in `efm/hasher.py` (the hash format constants are already there).
  - `hasher.hash(path)` replaces `store.hash_file(path)`, using the stat cache and counting `HashStats`.
  - `hash_contents(path)` becomes a plain function (no cache), for scratch files and store copies.
- No root dir or store on the hasher: make one (`hasher = Hasher()`) and pass it down where needed, next to the store. No singleton (global state tests would have to reset), and no `StoreHasher.get(store)` lookup, since a hasher has no reason to belong to a store.
  - Open question: `Hasher()` taking no arguments means it has to find the stat cache itself, but `--no-stat-cache` still needs a way to turn it off.
- `Store` loses `stat_cache`, `stats`, and `hash_file`. Callers to update: `listing.py` (`open_store`, `read_rows`) and `commands/acsm.py`.
- Move the hashing tests from `tests/test_store.py` to a `tests/test_hasher.py`.

## StatCache

- It isn't specific to books; that's only naming (`book`, `_book_dir`). Rename those to `path`.
- The hash-format check on cached values has already moved into `StatCache.get`.
