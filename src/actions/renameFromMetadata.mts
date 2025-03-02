import fs from "node:fs";
import getMetadata from "../epub/getMetadata.mjs";
import Logger from "../logger.mjs";
import path from "node:path";

export default async function renameFromMetadata(
  filepath: string,
  options: { dry: boolean },
): Promise<string> {
  if (filepath.endsWith(".epub")) {
    const { title, author } = await getMetadata(filepath, options);
    const newFilepath = path.join(
      path.dirname(filepath),
      `${author} - ${title}.epub`,
    );
    if (options.dry) {
      console.log("rename", filepath, "to", newFilepath);
      return filepath;
    }
    fs.renameSync(filepath, newFilepath);
    return newFilepath;
  }
  Logger.error("can't get metadata for", filepath);
  return filepath;
}
