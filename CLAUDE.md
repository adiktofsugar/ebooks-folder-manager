# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ebooks Folder Manager (EFM) is a Calibre replacement that provides minimal metadata management for ebooks. It is a CLI-only tool. Books stay where they are; efm keeps their metadata in a central store keyed by content hash (see `docs/store.md`). `efm ls <dir>` lists the books in one directory with their metadata; `efm find <dir>` recurses and filters by path or metadata. Actions are meant to be run manually, one subcommand each. `efm acsm` is the first one ported to the store; the rest (dedrm, rename, ...) haven't been yet.

## Architecture

### Python Backend (`efm/`)
- Subcommand-based CLI. `efm/__main__.py` sets up `sys.path`, logging (to stderr), global options (`--loglevel`, `--store`, `--no-stat-cache`), and dispatches to `efm/commands/`:
  - `commands/ls.py`: `efm ls [path ...]` - list books in one directory (not recursive), like `ls`
  - `commands/find.py`: `efm find <dir> [pattern ...]` - recursive listing with path and metadata filters (`--title`, `--author`, `--book-format`, `--encrypted`, `--missing`)
  - Both use `listing.py` for store reads and output (`--raw`, `-f line|table|json`; default `line` is tab-separated file/title/author, one per line)
  - `commands/acsm.py`: `efm acsm <file ...>` - fulfill .acsm tokens and replace each with the downloaded book (see "Commands that replace books" in `docs/store.md`)
  - `commands/setup.py`: `efm setup [tool]` - DRM key extraction/config menu (or run one tool directly)
  - New subcommands expose `add_parser(subparsers)` and `run(args, console) -> int`, and get registered in `create_parser()`
- Core modules:
  - `store.py`: Hash-keyed metadata store (`load`, `put`, `put_content`; `StoreEntry` with lazy `metadata`/`metadata_internal`/`metadata_raw`/`ancestor`)
  - `hasher.py`: `Hasher().hash(path)` (uses `StatCache`, a path+stat → hash cache, so unchanged files aren't re-hashed) and uncached `hash_contents(path)`; make one per run and pass it down
  - `scratch.py`: `scratch_dir(label)` context manager; deleted on success, kept on failure
  - `acsm.py`: ACSM fulfillment via `adl` (imported lazily; importing it creates adl's data dir)
  - `metadata.py`: Versioned metadata models + migrations, and extraction via PyMuPDF (supports PDF, XPS, EPUB, MOBI, FB2, CBZ, SVG, TXT)
  - `dedrm.py`: DRM removal functionality
  - `action.py`: Base class and implementations for processing actions (not yet wired to a command)
  - `kfxconvert.py`: Kindle format conversion
  - `config.py`: Configuration management (supports TOML, YAML, JSON)
  - `env.py`: Environment setup utilities
  - `exceptions.py`: Custom exception classes

### External Libraries
- `DeDRM_tools/`: DRM removal plugins (Calibre plugin)
- `kfxlib/`: Kindle format handling
- `adl/`: Adobe Digital Library tools

## Common Development Commands

### Setup
```bash
git submodule update --init   # adl/ and DeDRM_tools/ are submodules
uv sync              # Install deps + efm in development mode
uv run efm --help    # Run the CLI tool
```

### Testing
```bash
# Run Python tests
uv run pytest               # Run all tests
uv run pytest -xvs          # Stop on first failure with verbose output
uv run pytest tests/test_metadata.py  # Run specific test file
```

### Listing Books
```bash
uv run efm ls path/to/books                  # One line per book directly in the dir (file, title, author)
uv run efm ls path/to/books -f table         # Table with full metadata
uv run efm ls path/to/books -f json          # JSON on stdout (logs go to stderr)
uv run efm ls path/to/books --raw -f table   # Raw pymupdf metadata
uv run efm find path/to/books                # Recursive
uv run efm find path/to/books 'foo.+epub'    # Only paths matching a filter
uv run efm find path/to/books --author foo   # Metadata filter (case-insensitive regex)
uv run efm --store /tmp/store ls path/to/books          # Global options go before the subcommand
uv run efm --loglevel debug --no-stat-cache find books  # Timing: hashed vs. cached

# DRM-related tools
uv run efm setup             # Interactive menu
uv run efm setup --help      # List tools (adobe-key, epub-test, epub-decrypt, ...)
uv run efm setup epub-test   # Run one tool directly
uv run efm acsm path/to/book.acsm   # Fulfill and replace with book.epub
```

### Python Development
```bash
# Type checking
uv run pyright       # Run Python type checker

# Linting
uv run ruff check efm     # Check Python code
uv run ruff format efm    # Format Python code
```

## Store Layout

See `docs/store.md`. In short:
- `$store/xx_<hash>/metadata.json`, `metadata_internal.json`, `metadata_raw.json`, optional `ancestor` and `content` (store: `--store`, `$EFM_STORE`, or `$XDG_DATA_HOME/efm/store`)
- `$XDG_CACHE_HOME/efm/stat-cache/<abs path>/<size>-<mtime_ns>-<ctime_ns>` contains the hash

## Key Technical Considerations

1. **File Safety**: `ls`/`find` only read books and write to the store and stat cache. Commands that replace a book (`acsm`) must first copy the original into the store (`Store.put_content`), and do their work in a `scratch_dir`.

2. **Metadata Flow**: file → `Hasher.hash` → `Store.load(h)`, or on a miss `StoreEntry.from_book(path)` + `Store.put(h, entry)`.

3. **Schema versions**: `metadata.json`/`metadata_internal.json` are versioned pydantic models (`MetadataV1`, ...; `Metadata` is the current alias). Changing a stored model means adding a new version plus a migration; see `docs/store.md`.

4. **DRM Handling**: The project includes DRM removal tools from Calibre. These should be used responsibly and legally.

5. **Configuration**: Supports `efm.toml`, `efm.yaml`, `efm.yml`, or `efm.json` for configuration (e.g., Adobe key file paths). `get_config(dir)` starts at the nearest config at or above `dir` and fills missing keys from configs further up.

6. **Python Version**: Requires Python 3.13+ and uses `uv` as the package manager.

## Testing Resources

Sample books for testing are available in `sample-books/` directory.

## Configuration Format

The configuration file supports various DRM key paths:
- `adobekey`: Path to Adobe DRM key file
- `kindlekey`: Path to Kindle DRM key file
- Additional DRM-related settings

## Known Limitations

- Actions (dedrm, rename, k2pdfopt) exist in `action.py` but have no subcommands yet
- Some ebooks may lack title/author metadata
- DRM removal for certain Kindle formats may not work
- Multiple format support (same book in EPUB/PDF) is planned but not implemented

## Development Tips
- Use uv efm to run any python program
- Use uv add to add dependencies
- Use the uv commands to run python scripts

## Execution Notes
- You have to run efm with uv run efm

## Execution Warnings
- You MUST NEVER directly invoke a python script. ALWAYS use uv

## Testing Memories
- run pytest with uv run pytest

## Linting Memories
- to run python lint, use `uv run scripts/lint.py`

## Python Test Running Memories
- to run python tests, use `uv run scripts/test.py`

## Execution Guideline Memories
- You MUST NEVER run python or python3 directly. ALWAYS run with uv.

## Python Development Memories
- don't use List from typing. it's deprecated