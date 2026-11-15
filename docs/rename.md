# efm rename

`efm rename` moves books to paths built from their metadata. It's meant to be run on a whole library:

```
efm rename -n ~/ebooks          # dry run: print "old -> new", change nothing
efm rename ~/ebooks             # default preset
efm rename -p comic ~/ebooks/comics
efm rename -f '{author}/{title}{ext}' ~/ebooks
efm rnm ...                     # alias
```

## Templates

A template is a path with `{placeholders}`. Everything outside the braces is literal, and `/` separates folders.

- `{title}`: a variable.
- `{series_index:02}`: a variable with a Python format spec, giving `03`. Specs work like they do in f-strings.
- `{author.split(', ')[0]}`: any small expression. You can use string methods, indexing and slicing, `and`/`or`/`not`, comparisons, `x if cond else y`, and the functions `len`, `str`, `int`, `float`, `min`, `max`, and `round`.
- `{{` and `}}`: a literal brace.

Expressions are evaluated with [simpleeval](https://github.com/danthedeckie/simpleeval), not `eval`. A config file could come from a downloaded folder, so it must not be able to run code. `_`-prefixed attributes and imports aren't available.

Surrounding whitespace in a template is ignored, so YAML `|` blocks work. Newlines and tabs inside a value become single spaces. A `/` inside a value becomes `_`, so a title like "AC/DC" doesn't create a folder. A template that renders to an absolute path, or to one with empty, `.`, or `..` components, is an error.

### Variables

| Variable | |
| --- | --- |
| `title`, `author`, `subject`, `keywords` | from the book's metadata |
| `series`, `series_index` | EPUB (EPUB3 `belongs-to-collection`, or calibre's `calibre:series`) and CBZ (`ComicInfo.xml`). `series_index` is a number (`3`, `1.5`) |
| `kind` | `epub2`, `epub3`, `pdf`, `cbz`, `mobi`, ... |
| `format`, `encryption`, `creator`, `producer`, `creation_date`, `mod_date`, `page_count`, `size` | from the book's metadata |
| `ext`, `stem`, `name` | the book's current suffix (with the dot), filename without suffix, and filename |

Run `efm ls -f table` to see what a book has.

### Missing values

If a placeholder needs a value the book doesn't have, that book is skipped with an error that names the missing variable (`{series}: missing series`). Every other book is still renamed. To handle books without a series, use variants (below), or an expression such as `{series or 'No Series'}`.

## Presets

Presets live under `rename` in `efm.toml` / `efm.yaml`, which is searched for upwards from the root directory. A preset is either a template, or a list of variants:

```yaml
rename:
  default_preset: series_first
  presets:
    series_first:
      - if: series
        value: '{series}/{series_index:02} - {title} - {author}{ext}'
      - if: title.startswith('The ')
        value: '{title[4:]}, The - {author}{ext}'
      - '{title} - {author}{ext}'
    comic: '{series}/{series} #{series_index:03}{ext}'
```

```toml
[rename]
default_preset = "series_first"

[rename.presets]
series_first = [
  { if = "series", value = "{series}/{series_index:02} - {title}{ext}" },
  "{title}{ext}",
]
```

Variants are tried in order, and the first one whose `if` is true wins. A plain string always matches. Inside an `if`, a missing variable is just `None`, which is false. An expression that fails, such as `series.lower()` when there's no series, is an error, not false: write `series and series.lower() == 'x'`. If no variant matches, that book is skipped.

The template to use is chosen in this order: `-f`, then `-p NAME`, then `rename.default_preset`, then a preset named `default`. Every template is checked before anything moves, so a typo fails the whole run.

Configs are merged by top-level key, so a nearer config's `rename` section replaces a parent's entirely. It isn't merged preset by preset.

## Where books go

Paths are relative to the **root**:
- For a directory operand, the root is that directory, and the directory is searched recursively.
- `--root DIR` overrides it, for example to sort one subdirectory into the library: `efm rename ~/ebooks/inbox --root ~/ebooks`.
- For a file operand, the root is the file's parent, and the template can't create folders. That case is ambiguous: the parent might already be a series folder. Pass `--root` for templates with folders.

Folders left empty by a move are removed, up to (but not including) the root.

## Collisions

- When a book is already at its target path, nothing happens. Running rename twice is a no-op.
- If two books render to the same path, both are skipped with an error.
- If the target exists and is a different file, the book is skipped with an error. If the target has the same content (same hash), it's a duplicate and gets replaced.

Moving a book doesn't change its content, so nothing new goes into the store. The stat cache is updated for the new path.
