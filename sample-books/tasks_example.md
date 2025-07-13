# Book Processing Tasks

This file demonstrates the new task format with parameters support.

## Task Format

The table now supports three columns:
- `description`: The task name (e.g., generate_covers, set_cover)
- `parameters`: Optional parameters for the task
- `status`: Task status (empty, in progress, success, error)

## Example Tasks

| description | parameters | status |
|-------------|------------|--------|
| generate_covers | | |
| update_metadata | | |
| set_cover | cover.png,sample.epub | |
| set_cover | https://example.com/cover.jpg,another-book.pdf | |
| check_duplicates | | |
| validate_formats | | |

## Parameter Format for set_cover

The `set_cover` task expects parameters in the format: `cover_source,book_path`

Where:
- `cover_source` can be:
  - A relative path to an image file (e.g., `cover.png`)
  - An absolute path to an image file (e.g., `/home/user/covers/cover.jpg`)
  - A URL to download the cover from (e.g., `https://example.com/cover.jpg`)
- `book_path` is the path to the book file relative to the directory being processed

## Usage

1. Create a `tasks.md` file in your book directory
2. Add tasks to the table
3. Run `efm` on the directory
4. The tool will process pending tasks and update their status