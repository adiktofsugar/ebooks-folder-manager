# Tests for Ebooks Folder Manager

This directory contains tests for the Ebooks Folder Manager (efm) application.

## Running Tests

This project uses Poetry for dependency management and running tests. To run the tests:

1. Make sure you have Poetry installed. If not, follow the instructions at [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation).

2. Install the project dependencies:

```bash
poetry install
```

3. Run the tests using Poetry:

```bash
poetry run pytest
```

Or to run with more verbose output (this is the default in our configuration):

```bash
poetry run pytest
```

You can also run a specific test file:

```bash
poetry run pytest tests/test_book.py
```

## Test Files

- `test_book.py`: Tests for the `Book` class in `efm/book.py`
  - Tests book initialization
  - Tests metadata extraction from EPUB and PDF files
  - Tests DRM removal functionality
  - Tests book renaming functionality
  - Tests the processing of various actions

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