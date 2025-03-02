import _ from "lodash";
import { strFromU8, type Unzipped } from "fflate";
import { XMLParser } from "fast-xml-parser";

export default async function getMetadataV3(
  unzipped: Unzipped,
  { filepath }: { dry: boolean; rootfilePath: string; filepath: string },
) {
  let metadataXml = "";
  for (const [filename, fileData] of Object.entries(unzipped)) {
    if (filename.endsWith("content.opf")) {
      metadataXml = strFromU8(fileData);
      break;
    }
  }

  if (!metadataXml) {
    throw new Error(`Metadata file not found in EPUB at path: ${filepath}`);
  }

  const parser = new XMLParser({
    ignoreAttributes: false,
    alwaysCreateTextNode: true,
  });
  const parsedXml = parser.parse(metadataXml);
  const metadata = parsedXml.package.metadata;
  // const series = metadata['meta']?.find((meta: any) => meta.name === 'calibre:series')?.content;

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
