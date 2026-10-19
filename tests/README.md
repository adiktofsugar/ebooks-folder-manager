# Tests for Ebooks Folder Manager

This directory contains tests for the Ebooks Folder Manager (efm) application.

## Running Tests

This project uses [uv](https://docs.astral.sh/uv/). From the repo root:

```bash
uv run scripts/test.py              # Run all tests
uv run scripts/test.py -w           # Re-run on file changes
uv run scripts/test.py cover        # Only test files matching "cover"
uv run pytest tests/test_cli.py     # Plain pytest also works
```

The DRM code lives in git submodules, so run `git submodule update --init` first.

## Sample Books

The tests use sample books from the `sample-books` directory:

- `1Q84.epub`
- `Emotions.pdf`
- `InterestingTimes.epub`
- `WorldUnbound.epub`

## Adding New Tests

When adding new tests:

1. Create a new test file with the prefix `test_` (e.g., `test_config.py`)
2. Use pytest fixtures for setup and teardown
3. Use descriptive test function names with the prefix `test_`
4. Add appropriate docstrings to explain what each test is checking