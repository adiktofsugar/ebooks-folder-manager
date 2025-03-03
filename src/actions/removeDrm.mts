import fs from "node:fs";
import { execSync } from "node:child_process";
import Logger from "../logger.mjs";
import { fileURLToPath } from "node:url";
import getBackupFilepath from "../lib/getBackupFilepath.mjs";
import PoetryRunner from "../lib/PoetryRunner.mjs";

const poetryRunner = new PoetryRunner(
  fileURLToPath(new URL("../../dedrm", import.meta.url)),
);

export default function removeDrm(
  filepath: string,
  options: { dry: boolean; adobeKeyFilepath?: string },
): string {
  if (options.dry) {
    console.log("remove drm for", filepath);
    return filepath;
  }
  if (filepath.endsWith(".epub")) {
    const drmKind = poetryRunner
      .run("epubtest", [filepath])
      .toString()
      .trim()
      .toLowerCase();
    if (drmKind === "adobe") {
      // TODO: actually get key...but that might be more of a setup thing where I generate a config file...
      const keyFilepath = options.adobeKeyFilepath;
      if (!keyFilepath) {
        throw new Error("No Adobe key file specified");
      }

      const nextFilepath = `${filepath.replace(/\.epub$/, "-dedrm.epub")}`;
      poetryRunner.run("epubdecrypt", [keyFilepath, filepath, nextFilepath]);

      const backupFilepath = getBackupFilepath(filepath);
      Logger.info(
        "removed DRM from",
        filepath,
        "backing up to",
        backupFilepath,
      );
      fs.renameSync(filepath, backupFilepath);
      fs.renameSync(nextFilepath, filepath);

      return filepath;
    }
    if (drmKind === "unencrypted") {
      Logger.debug("no DRM to remove for", filepath);
      return filepath;
    }
    throw new Error(`Unknown DRM kind: ${drmKind}`);
  }
  Logger.error("unknown file extension", filepath);
  return filepath;
}
