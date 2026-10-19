# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ebooks Folder Manager (EFM) is a Calibre replacement that provides minimal metadata management for ebooks. It is a CLI-only tool: it processes a folder of books into an output library (SHA-named book copies plus a `db.yaml` metadata database) without rewriting the original files. There is no web UI in this repo; `db.yaml` is the intended interface for any external viewer.

## Architecture

### Python Backend (`efm/`)
- Subcommand-based CLI. `efm/__main__.py` sets up `sys.path`, logging, and dispatches to `efm/commands/`:
  - `commands/process.py`: `efm process` - process a directory of books into an output library
  - `commands/setup.py`: `efm setup [tool]` - DRM key extraction/config menu (or run one tool directly)
  - New subcommands expose `add_parser(subparsers)` and `run(args, console) -> int`, and get registered in `create_parser()`
- Core modules:
  - `transaction.py`: Processes individual ebooks with caching and result handling
  - `metadata.py`: Extracts metadata using PyMuPDF (supports PDF, XPS, EPUB, MOBI, FB2, CBZ, SVG, TXT)
  - `dedrm.py`: DRM removal functionality
  - `action.py`: Base class and implementations for processing actions
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

### Processing Books
```bash
uv run efm process path/to/books -o out              # Process books in directory
uv run efm process path/to/books -o out 'foo.+epub'  # Only process files matching a filter
uv run efm --loglevel debug process path/to/books    # Global options go before the subcommand

# DRM-related tools
uv run efm setup             # Interactive menu
uv run efm setup --help      # List tools (adobe-key, epub-test, epub-decrypt, ...)
uv run efm setup epub-test   # Run one tool directly
```

### Python Development
```bash
# Type checking
uv run pyright       # Run Python type checker

# Linting
uv run ruff check efm     # Check Python code
uv run ruff format efm    # Format Python code
```

## Output Structure

The output directory contains:
- `books/`: Processed ebooks (named `Author-Title.ext`, falling back to the original stem) and cover images (named by SHA hash)
- `_cache/`: Individual book metadata (YAML files)
- `db.yaml`: Consolidated metadata database

## Key Technical Considerations

1. **File Safety**: Original files are never modified. Books are copied to `<output>/books/`; duplicates are detected by content hash.

2. **Metadata Flow**: 
   - Individual book metadata → `_cache/*.yaml`
   - Consolidated database → `db.yaml`

3. **DRM Handling**: The project includes DRM removal tools from Calibre. These should be used responsibly and legally.

4. **Configuration**: Supports `efm.toml`, `efm.yaml`, `efm.yml`, or `efm.json` for configuration (e.g., Adobe key file paths).

5. **Python Version**: Requires Python 3.13+ and uses `uv` as the package manager.

## Testing Resources

Sample books for testing are available in `sample-books/` directory.

## Configuration Format

The configuration file supports various DRM key paths:
- `adobekey`: Path to Adobe DRM key file
- `kindlekey`: Path to Kindle DRM key file
- Additional DRM-related settings

## Known Limitations

- File renaming can overwrite existing files
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