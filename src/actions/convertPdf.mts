import fs from "node:fs";
import { execSync } from "node:child_process";
import Logger from "../logger.mjs";
import getBackupFilepath from "../lib/getBackupFilepath.mjs";
import Metadata from "../pdf/Metadata.mjs";

export default function convertPdf(
  filepath: string,
  options: { dry: boolean; adobeKeyFilepath?: string },
): string {
  if (options.dry) {
    console.log("run k2pdfopt on", filepath);
    return filepath;
  }
  if (filepath.endsWith(".pdf")) {
    const metadata = new Metadata(filepath);
    const { isK2pdfoptVersion } = metadata.getMetadata();
    if (isK2pdfoptVersion) {
      Logger.debug("this is the converted version. Skipping.");
      return filepath;
    }
    const nextFilepath = `${filepath.replace(/\.pdf$/, "-k2pdfopt.pdf")}`;
    execSync(
      // -om = output margin
      // -ds = document scale
      // -w = width of reader
      // -h = height of reader
      // -o = output file
      `k2pdfopt -om 0.1 -ds 0.5 -w 1264 -h 1680 -o "${nextFilepath}" "${filepath}"`,
      // need to ignore stdin so it doesn't go into interactive mode
      { stdio: ["ignore", "inherit", "inherit"] },
    );
    const nextMetadata = new Metadata(nextFilepath);
    nextMetadata.setMetadata({ isK2pdfoptVersion: true });
    const backupFilepath = getBackupFilepath(filepath);
    Logger.info("converted", filepath, "backing up to", backupFilepath);
    fs.renameSync(filepath, backupFilepath);
    fs.renameSync(nextFilepath, filepath);
  }
  Logger.debug("skip non pdf file", filepath);
  return filepath;
}
