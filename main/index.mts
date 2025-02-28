import fs from "node:fs";
import path from "node:path";
import walkdir from "walkdir";
import type { Action } from "./interfaces.mjs";
import Logger from "./logger.mjs";
import removeDrm from "./actions/removeDrm.mjs";

export default async function run(
  dirpath: string,
  options: { dry: boolean; watch: boolean },
  actions: Action[],
) {
  const promises: Promise<unknown>[] = [];
  const foundDirpaths: string[] = [];
  await new Promise((resolve, reject) => {
    walkdir(dirpath)
      .on("file", (filepath: string) => {
        promises.push(runOnFile(filepath, options, actions));
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
  await Promise.all(promises);
  if (options.watch) {
    for (const foundDirpath of foundDirpaths) {
      console.error("watching", foundDirpath);
      fs.watch(foundDirpath, (event, filename) => {
        if (filename) {
          const filepath = path.join(foundDirpath, filename);
          // filename is the name of the file that triggered the event
          // rename is usually when a file is added or removed
          // change is usually when a file is modified
          if (fs.existsSync(filepath)) {
            runOnFile(foundDirpath, options, actions);
          }
        }
      });
    }
    // I think node just stays open when watchers are installed?
  }
}

async function runOnFile(
  filepath: string,
  options: { dry: boolean },
  actions: Action[],
) {
  for (const action of actions) {
    if (action.type === "drm") {
      await removeDrm(filepath, options);
    }
    if (action.type === "rename") {
      await runRename(filepath, options);
    }
    if (action.type === "print") {
      await runPrint(filepath, options, action.filename);
    }
  }
}
