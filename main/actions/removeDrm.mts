import Logger from "../logger.mjs";

export default function removeDrm(filepath: string, options: { dry: boolean }) {
  if (options.dry) {
    console.log("remove drm for", filepath);
    return;
  }
  if (filepath.endsWith(".epub")) {
    Logger.info("removing drm for epub", filepath);
  } else {
    Logger.error("can't remove drm for", filepath);
  }
}
