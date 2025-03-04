import fs from "node:fs";
import path from "node:path";
import walkdir from "walkdir";
import type { Action } from "./interfaces.mjs";
import Book from "./Book.mjs";

export default async function run(
  dirpath: string,
  options: { dry: boolean; watch: boolean; adobeKeyFilepath?: string },
  actions: Action[],
) {
  const foundDirpaths: string[] = [];
  const books: Book[] = [];
  await new Promise((resolve, reject) => {
    walkdir(dirpath)
      .on("file", (filepath: string) => {
        books.push(
          new Book(filepath, {
            adobeKeyFilepath: options.adobeKeyFilepath,
            dry: options.dry,
          }),
        );
      })
      .on("directory", (dirpath: string) => {
        foundDirpaths.push(dirpath);
      })
      .on("end", () => {
        resolve(null);
      })
      .on("error", (err: Error) => {
        reject(err);
      });
  });
  for (const book of books) {
    await processBook(book, actions);
  }
  if (options.watch) {
    console.error("done. watching.");
    for (const foundDirpath of foundDirpaths) {
      console.error("watching", foundDirpath);
      fs.watch(foundDirpath, (event, filename) => {
        if (filename) {
          const filepath = path.join(foundDirpath, filename);
          // filename is the name of the file that triggered the event
          // rename is usually when a file is added or removed
          // change is usually when a file is modified
          if (fs.existsSync(filepath)) {
            let book = books.find((book) => book.sourceFilepath === filepath);
            if (!book) {
              book = new Book(filepath, {
                adobeKeyFilepath: options.adobeKeyFilepath,
                dry: options.dry,
              });
              books.push(book);
            }
            processBook(book, actions);
          }
        }
      });
    }
    // I think node just stays open when watchers are installed?
  }
}

async function processBook(book: Book, actions: Action[]) {
  for (const action of actions) {
    // Need to do drm first if we're going to do anything else after...
    if (action.type === "drm") {
      await book.removeDrm();
    }
    if (action.type === "none") {
      await book.getMetadata();
    }
    if (action.type === "print") {
      await book.printMetadata();
    }
    if (action.type === "rename") {
      await book.renameFromMetadata();
    }
    if (action.type === "pdf") {
      await book.convertPdf();
    }
  }
  await book.save();
}
