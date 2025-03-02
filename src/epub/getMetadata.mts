import { promises as fs } from "node:fs";
import { unzipSync, strFromU8 } from "fflate";
import { XMLParser } from "fast-xml-parser";
import getMetadataV3 from "./getMetadataV3.mjs";
import getMetadataV2 from "./getMetadataV2.mjs";

export default async function getMetadata(
  filepath: string,
  options: { dry: boolean },
) {
  // Read the EPUB file
  const data = await fs.readFile(filepath);

  // Unzip the EPUB file
  const unzipped = unzipSync(new Uint8Array(data));

  // Find the container.xml file
  const containerFile = unzipped["META-INF/container.xml"];
  if (!containerFile) {
    throw new Error(`container.xml not found in EPUB file - ${filepath}`);
  }

  // Parse the container.xml file
  const parser = new XMLParser({ ignoreAttributes: false });
  const containerContent = strFromU8(containerFile);
  const containerJson = parser.parse(containerContent);

  // Extract the rootfile path
  const rootfilePath: string =
    containerJson.container.rootfiles.rootfile["@_full-path"];
  if (!rootfilePath) {
    throw new Error(`Rootfile path not found in container.xml - ${filepath}`);
  }

  // Find the rootfile
  const rootfile = unzipped[rootfilePath];
  if (!rootfile) {
    throw new Error(`Rootfile not found in EPUB file - ${filepath}`);
  }

  // Parse the rootfile
  const rootfileContent = strFromU8(rootfile);
  const rootfileJson = parser.parse(rootfileContent);

  // Determine the EPUB version
  const version = rootfileJson.package["@_version"];
  if (!version) {
    throw new Error(`EPUB version not found in rootfile - ${filepath}`);
  }

  // Return the major version as a number
  const epubVersion = Number.parseInt(version.split(".")[0], 10);
  if (Number.isNaN(epubVersion)) {
    throw new Error(`Invalid EPUB version - ${filepath}`);
  }
  const extOptions = {
    ...options,
    rootfilePath,
    filepath,
  };
  if (epubVersion === 3) {
    return getMetadataV3(unzipped, extOptions);
  }
  if (epubVersion === 2) {
    return getMetadataV2(unzipped, extOptions);
  }
  throw new Error(`Unsupported EPUB version - ${version} - ${filepath}`);
}
