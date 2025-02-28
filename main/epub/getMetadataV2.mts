import _ from "lodash";
import { type Unzipped, strFromU8 } from "fflate";
import { XMLParser } from "fast-xml-parser";

export default async function getMetadataV2(
  unzipped: Unzipped,
  {
    rootfilePath,
    filepath,
  }: { dry: boolean; rootfilePath: string; filepath: string },
) {
  // Find the rootfile
  const rootfile = unzipped[rootfilePath];
  if (!rootfile) {
    throw new Error(`Rootfile not found in EPUB file - ${filepath}`);
  }

  const parser = new XMLParser({
    ignoreAttributes: false,
    alwaysCreateTextNode: true,
  });

  // Parse the rootfile
  const rootfileContent = strFromU8(rootfile);
  const rootfileJson = parser.parse(rootfileContent);

  // Extract metadata
  const metadata = rootfileJson.package.metadata;
  if (!metadata) {
    throw new Error(`Metadata not found in rootfile - ${filepath}`);
  }

  const title: string = metadata["dc:title"]["#text"];
  const author: string = metadata["dc:creator"]["#text"];
  const identifiers: string[] = _.castArray(metadata["dc:identifier"]).map(
    (node: Record<string, string>) => {
      const scheme = node["@_opf:scheme"];
      return [scheme, node["#text"]].filter(Boolean).join(": ");
    },
  );
  const language: string = metadata["dc:language"]?.["#text"];
  const publisher: string = metadata["dc:publisher"]?.["#text"];

  return { title, author, identifiers, language, publisher };
}
