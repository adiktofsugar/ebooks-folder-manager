import { execSync } from "child_process";
import Logger from "../logger.mjs";
import { fileURLToPath } from "url";

// NOTE: is this still true when built?
const dedrmProjectDirpath = fileURLToPath(new URL("../../dedrm", import.meta.url));

export default function removeDrm(
  filepath: string,
  options: { dry: boolean, adobeKeyFilepath?: string },
): string {
  if (options.dry) {
    console.log("remove drm for", filepath);
    return filepath;
  }
  if (filepath.endsWith(".epub")) {
    const drmKind = runDeDrmScript(`epubtest`, [filepath]).toString().trim().toLowerCase();
    if (drmKind === 'adobe') {
      const keyFilepath = options.adobeKeyFilepath;
      if (!keyFilepath) {
        throw new Error("No Adobe key file specified");
      }
      const newFilepath = filepath.replace(/\.epub$/, ".nodrm.epub");
      runDeDrmScript(`epubdecrypt`, [keyFilepath, filepath, newFilepath]);
      return newFilepath;
    }
    if (drmKind === 'unencrypted') {
      Logger.debug("no DRM to remove for", filepath);
      return filepath;
    }
    throw new Error(`Unknown DRM kind: ${drmKind}`);
  } else {
    Logger.error("can't remove drm for", filepath);
  }
  return filepath;
}

function runDeDrmScript(scriptName:string, args:string[]) {
  return execSync(`poetry -P "${dedrmProjectDirpath}" run "${scriptName}" ${args.map(a => `"${a}"`).join(" ")}`);
}