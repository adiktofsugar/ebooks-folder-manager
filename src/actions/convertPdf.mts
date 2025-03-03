import fs from "node:fs";
import { execSync } from "node:child_process";
import Logger from "../logger.mjs";
import getBackupFilepath from "../lib/getBackupFilepath.mjs";
import Metadata from "../pdf/Metadata.mjs";
import path from "node:path";

export default function convertPdf(
  filepath: string,
  options: { dry: boolean; adobeKeyFilepath?: string },
): string {
  if (options.dry) {
    console.log("run k2pdfopt on", filepath);
    return filepath;
  }
  if (filepath.endsWith(".pdf")) {
    Logger.debug("pdf - getting metadata for", filepath);
    const metadata = new Metadata(filepath);
    const { isK2pdfoptVersion } = metadata.getMetadata();
    if (isK2pdfoptVersion) {
      Logger.debug("pdf - this is the converted version. Skipping.");
      return filepath;
    }
    // This outFilepath has to be in the same directory to avoid "cross-device link" errors
    let outFilepath: string;
    do {
      outFilepath = path.join(
        path.dirname(filepath),
        `${crypto.randomUUID()}-k2pdfopt.pdf`,
      );
    } while (fs.existsSync(outFilepath));
    Logger.info(
      "pdf - running k2pdfopt on",
      filepath,
      "output to",
      outFilepath,
    );
    execSync(
      // -om = output margin
      // -ds = document scale
      // -w = width of reader
      // -h = height of reader
      // -o = output file
      `k2pdfopt -om 0.1 -ds 0.5 -w 1264 -h 1680 -o "${outFilepath}" "${filepath}"`,
      // need to ignore stdin so it doesn't go into interactive mode
      { stdio: ["ignore", "ignore", "inherit"] },
    );
    Logger.debug("pdf - ran k2pdfopt on", filepath, "output to", outFilepath);
    const outMetadata = new Metadata(outFilepath);
    outMetadata.setMetadata({ isK2pdfoptVersion: true });
    const backupFilepath = getBackupFilepath(filepath);
    Logger.info("pdf - converted", filepath, "backed up to", backupFilepath);
    fs.renameSync(filepath, backupFilepath);
    fs.renameSync(outFilepath, filepath);
    return filepath;
  }
  Logger.debug("pdf - skipping non-pdf", filepath);
  return filepath;
}
