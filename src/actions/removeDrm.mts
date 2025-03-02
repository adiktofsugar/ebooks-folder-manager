import path from "node:path";
import { execSync } from "node:child_process";
import Logger from "../logger.mjs";
import { fileURLToPath } from "node:url";

const poetryFilepath = fileURLToPath(
  new URL("../../bin/poetry", import.meta.url),
);
const dedrmProjectDirpath = fileURLToPath(
  new URL("../../dedrm", import.meta.url),
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
    const drmKind = runDeDrmScript("epubtest", [filepath])
      .toString()
      .trim()
      .toLowerCase();
    if (drmKind === "adobe") {
      // TODO: actually get key...but that might be more of a setup thing where I generate a config file...
      const keyFilepath = options.adobeKeyFilepath;
      if (!keyFilepath) {
        throw new Error("No Adobe key file specified");
      }
      const newFilepath = filepath.replace(/\.epub$/, ".nodrm.epub");
      runDeDrmScript("epubdecrypt", [keyFilepath, filepath, newFilepath]);
      return newFilepath;
    }
    if (drmKind === "unencrypted") {
      Logger.debug("no DRM to remove for", filepath);
      return filepath;
    }
    throw new Error(`Unknown DRM kind: ${drmKind}`);
  }
  Logger.error("can't remove drm for", filepath);
  return filepath;
}

let hasRunInstall = false;
function runDeDrmScript(scriptName: string, args: string[]) {
  if (!hasRunInstall) {
    execSync(`${poetryFilepath} -P "${dedrmProjectDirpath}" install`);
    hasRunInstall = true;
  }
  return execSync(
    `${poetryFilepath} -P "${dedrmProjectDirpath}" run "${scriptName}" ${args.map((a) => `"${a}"`).join(" ")}`,
  );
}
