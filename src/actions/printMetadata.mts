import fs from "node:fs";
import getMetadata from "../lib/getMetadata.mjs";

export default async function printMetadata(
  filepath: string,
  options: { dry: boolean; outputFilepath?: string },
): Promise<string> {
  const metadata = await getMetadata(filepath);
  if (metadata) {
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
  }
  return filepath;
}
