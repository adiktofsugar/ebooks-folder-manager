I'm tired of calibre. All I want is to add minimal metadata to my books and keep them in a folder.

Rewriting the books all the time is not a great idea, though, because sometimes things go wrong, and when that happens, your books get destroyed. So, instead, I'll generate a static site from them.

The static site is a folder like this:

- index.html
- assets
  - index.js
- books
  - abc123.epub
- metadata
  - summary.json
  - abc123.json

The **index.html** is your entry point. There are no pages in this site, because navigation requires a backend.
The **assets** directory is where the js / css / images go.
The **books** directory is where your books, named as a sha of the contents of the original file, go.
The **metadata** directory is your "database". It's what the JS in the site will use to search and display your meta info.

# Known issues / Future features

## Multiple formats

Initially, this isn't supported. We'll list each format as a different book, like:

- Where the wild things are (epub)
- Where the wild things are (pdf)

This can, however, get annoying if you wanted to centralize the data. So I think the metadata will eventually contain an "alias" or "target" property that redirects you to a different doc for the info. For example:

```yaml
file: sha123.epub
title: Where the wild things are
year: 1990
description: null
```

```yaml
file: sha123.pdf
alias: sha123.epub
```

I'm not sure how you'd set this up though...hm. Maybe a config file? You'll need a config file for credentials anyway so that makes sense. The site can write to it to save preferences and all that.

## Sync to device

ebooks generally mount as a drive when connected to your computer, and then you can drag them over. The "sync to disk" option should be all you need to sync it to your mounted ebook. You could also copy the "books" directory, but then you'd have weird filenames.

## Books that have more than one output file

Apparently "topaz" books have an svg zip output. I guess metadata can have an "auxiliary_files" key or something?
