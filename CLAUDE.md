# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ebooks Folder Manager (EFM) is a Calibre replacement that provides minimal metadata management for ebooks and generates a static site for browsing. The project avoids repeatedly rewriting book files, instead generating a read-only static site from the original files.

## Architecture

### Python Backend (`efm/`)
- CLI tool for processing ebooks (entry point: `efm/__main__.py`)
- Core modules:
  - `transaction.py`: Processes individual ebooks
  - `metadata.py`: Extracts/manages ebook metadata
  - `dedrm.py`: DRM removal functionality
  - `action.py`: Different processing actions
  - `kfxconvert.py`: Kindle format conversion

### React Frontend (`site-ui/`)
- Static site UI with React 19 and MobX
- Fuzzy search functionality
- Displays books from YAML metadata

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
pytest               # Run all tests
pytest -xvs          # Stop on first failure with verbose output
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

6. **Monorepo Structure**: Uses Turbo for task orchestration across Python backend and JavaScript frontend.

## Testing Resources

Sample books for testing are available in `sample-books/` directory.

## Known Limitations

- File renaming can overwrite existing files
- Some ebooks may lack title/author metadata
- DRM removal for certain Kindle formats may not work
- Multiple format support (same book in EPUB/PDF) is planned but not implemented