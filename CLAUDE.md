# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ebooks Folder Manager (EFM) is a Calibre replacement that provides minimal metadata management for ebooks and generates a static site for browsing. The project avoids repeatedly rewriting book files, instead generating a read-only static site from the original files.

## Architecture

### Python Backend (`efm/`)
- CLI tool for processing ebooks (entry point: `efm/__main__.py`)
- Core modules:
  - `transaction.py`: Processes individual ebooks with caching and result handling
  - `metadata.py`: Extracts metadata using PyMuPDF (supports PDF, XPS, EPUB, MOBI, FB2, CBZ, SVG, TXT)
  - `dedrm.py`: DRM removal functionality
  - `action.py`: Base class and implementations for processing actions
  - `kfxconvert.py`: Kindle format conversion
  - `config.py`: Configuration management (supports TOML, YAML, JSON)
  - `env.py`: Environment setup utilities
  - `exceptions.py`: Custom exception classes

### React Frontend (`site-ui/`)
- Static site UI with React 19 and MobX
- TypeScript with custom ESBuild script (`scripts/esbuild.mts`)
- Key components:
  - `App.tsx`: Root component
  - `BookList.tsx`: Main book list with search
  - `BookListItem.tsx`: Individual book display
- Stores:
  - `DbStore.ts`: Fetches and manages book database
  - `BookListStore.ts`: Manages book list and fuzzy search

### External Libraries
- `DeDRM_tools/`: DRM removal plugins (Calibre plugin)
- `kfxlib/`: Kindle format handling
- `adl/`: Adobe Digital Library tools

## Common Development Commands

### Build and Development
```bash
# Install dependencies and run development servers
npm install
npm run dev          # Starts dev server with watch mode (uses Turbo)

# Build the static site
npm run build

# Lint and fix code
npm run lint         # Run Biome linter
npm run fix          # Auto-fix linting issues

# Python development (uses uv package manager)
uv pip install -e .  # Install in development mode
efm                  # Run the CLI tool
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
# Process ebooks (after installing with uv)
efm path/to/books    # Process books in directory
efm book.epub        # Process single book

# DRM-related tools
getadobekey          # Extract Adobe DRM keys
epubtest file.epub   # Test EPUB DRM type
epubdecrypt file.epub # Decrypt DRM-protected EPUB
```

### Python Development
```bash
# Type checking
uv run pyright       # Run Python type checker

# Linting
uv run ruff check efm     # Check Python code
uv run ruff format efm    # Format Python code
```

## Static Site Structure

The generated site in `site/` contains:
- `index.html`: Entry point
- `books/`: Processed ebooks (named by SHA hash)
- `_cache/`: Individual book metadata (YAML files)
- `db.yaml`: Consolidated metadata database
- JavaScript/CSS assets from the UI build

## Key Technical Considerations

1. **File Safety**: Original files are never modified. Books are copied to `site/books/` with SHA-based names to avoid duplicates.

2. **Metadata Flow**: 
   - Individual book metadata → `_cache/*.yaml`
   - Consolidated database → `db.yaml`
   - Frontend reads `db.yaml` to display books

3. **DRM Handling**: The project includes DRM removal tools from Calibre. These should be used responsibly and legally.

4. **Configuration**: Supports `efm.toml`, `efm.yaml`, `efm.yml`, or `efm.json` for configuration (e.g., Adobe key file paths).

5. **Python Version**: Requires Python 3.13+ and uses `uv` as the package manager.

6. **Monorepo Structure**: Uses Turbo for task orchestration across Python backend and JavaScript frontend. Check `package.json` for current workspaces configuration.

7. **Development Server**: The dev command starts both a Python HTTP server (port 8000) and watches for UI changes, automatically copying built assets to the `site/` directory.

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

## React Context and Store Guidelines
- You can add MobX stores to context, but there should be no other kind of react context

## Execution Warnings
- You MUST NEVER directly invoke a python script. ALWAYS use uv