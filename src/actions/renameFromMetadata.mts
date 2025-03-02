import fs from "node:fs";
import getMetadata from "../lib/getMetadata.mjs";
import Logger from "../logger.mjs";
import path from "node:path";

export default async function renameFromMetadata(
  filepath: string,
  options: { dry: boolean },
): Promise<string> {
  const metadata = await getMetadata(filepath);
  if (metadata) {
    const { title, creators } = metadata;
    const author = creators
      ? Array.isArray(creators)
        ? creators[0]
        : creators
      : "Unknown";
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
  return filepath;
}
