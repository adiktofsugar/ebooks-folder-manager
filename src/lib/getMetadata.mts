import getEpubMetadata from "../epub/getMetadata.mjs";
import Logger from "../logger.mjs";

export default async function getMetadata(filepath: string) {
  if (filepath.endsWith(".epub")) {
    return getEpubMetadata(filepath);
  }
  return null;
}
