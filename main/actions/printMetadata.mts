import fs from "node:fs";
import getMetadata from "../epub/getMetadata.mjs";
import Logger from "../logger.mjs";

export default async function printMetadata(
  filepath: string,
  options: { dry: boolean; outputFilepath?: string },
): Promise<string> {
  if (filepath.endsWith(".epub")) {
    const metadata = await getMetadata(filepath, options);
    if (options.outputFilepath) {
      if (options.dry) {
        console.log("write metadata to", options.outputFilepath);
      } else {
        fs.writeFileSync(
          options.outputFilepath,
          JSON.stringify(metadata, null, 2),
        );
      }
    } else {
      console.log(JSON.stringify(metadata, null, 2));
    }
    return filepath;
  }
  Logger.error("can't get metadata for", filepath);
  return filepath;
}
