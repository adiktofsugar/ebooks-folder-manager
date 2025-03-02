import { promises as fs } from "node:fs";
import { unzipSync, strFromU8 } from "fflate";
import { XMLParser } from "fast-xml-parser";
import _ from "lodash";
import type { XmlNode, XmlNodeValue } from "./interfaces.mjs";

export default async function getMetadata(filepath: string) {
  try {
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
    const parser = new XMLParser({
      ignoreAttributes: false,
      alwaysCreateTextNode: true,
      attributesGroupName: "attributes",
      attributeNamePrefix: "",
    });
    const containerContent = strFromU8(containerFile);
    const containerJson = parser.parse(containerContent) as XmlNode;

    // Extract the rootfile path
    const rootfilePath: string | undefined = (
      ((containerJson.container as XmlNode).rootfiles as XmlNode)
        .rootfile as XmlNodeValue
    ).attributes?.["full-path"];
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
    const rootfileJson = parser.parse(rootfileContent) as XmlNode;

    const packageNode = getPrefixedNode(
      rootfileJson,
      "package",
      "opf",
    ) as XmlNode;
    if (!packageNode) {
      throw new Error(`Invalid rootfile - no "package" - ${filepath}`);
    }
    const uniqueId = packageNode.attributes?.["unique-identifier"];
    if (!uniqueId) {
      throw new Error(`Unique identifier not found in rootfile - ${filepath}`);
    }

    // Determine the EPUB version
    const version = packageNode.attributes?.version;
    if (!version) {
      throw new Error(`EPUB version not found in rootfile - ${filepath}`);
    }

    // Return the major version as a number
    const epubVersion = Number.parseInt(version.split(".")[0], 10);
    if (Number.isNaN(epubVersion)) {
      throw new Error(`Invalid EPUB version - ${filepath}`);
    }

    // Extract metadata
    const metadata = getPrefixedNode(packageNode, "metadata", "opf") as XmlNode;
    if (!metadata) {
      throw new Error(`Metadata not found in rootfile - ${filepath}`);
    }
    const dcData = getDcNodesOpf(metadata);
    assertRequiredDcNodes(dcData, filepath);
    return dcData;
  } catch (e) {
    if (e instanceof Error) {
      e.message += ` - ${filepath}`;
    }
    throw e;
  }
}

/**
 * Get DC nodes as defined in the OPF specification.
 * @param metadata The metadata node from XMLParser
 * @param prefix The namespace for the Dublin Core nodes
 */
function getDcNodesOpf(metadata: XmlNode, prefix = "dc") {
  const titleRaw = getPrefixedNode(metadata, "title", prefix);
  const creatorRaw = getPrefixedNode(metadata, "creator", prefix);
  // const subjectRaw = getDcNode(metadata, "subject", prefix);
  // const descriptionRaw = getDcNode(metadata, "description", prefix);
  // const contributorRaw = getDcNode(metadata, "contributor", prefix);
  const dateRaw = getPrefixedNode(metadata, "date", prefix);
  // const typeRaw = getDcNode(metadata, "type", prefix);
  // const formatRaw = getDcNode(metadata, "format", prefix);
  const identifierRaw = getPrefixedNode(metadata, "identifier", prefix);
  const languageRaw = getPrefixedNode(metadata, "language", prefix);
  // const relationRaw = getDcNode(metadata, "relation", prefix);
  // const rightsRaw = getDcNode(metadata, "rights", prefix);

  let title: string | null = null;
  // must have one title
  if (titleRaw) {
    if (Array.isArray(titleRaw)) {
      // probably we should select the title with the best language, but for now, just the first
      title = titleRaw[0]["#text"];
    } else {
      title = titleRaw["#text"];
    }
  }
  // TODO: handle role attributes
  let creators: string | string[] | null = null;
  if (creatorRaw) {
    creators = Array.isArray(creatorRaw)
      ? creatorRaw.map((c) => c["#text"])
      : creatorRaw["#text"];
  }
  let dateOfPublication: Date | null = null;
  if (dateRaw) {
    // "Date and Time Formats" at http://www.w3.org/TR/NOTE-datetime and by ISO 8601 on which it is based.
    if (Array.isArray(dateRaw)) {
      const publicationDateNode = dateRaw.find(
        (d) => d.attributes?.["opf:event"] === "publication",
      );
      const dateNode = publicationDateNode || dateRaw[0];
      dateOfPublication = new Date(dateNode["#text"]);
    } else {
      dateOfPublication = new Date(dateRaw["#text"]);
    }
  }
  const identifiers: { id: string; scheme?: string }[] = [];
  if (identifierRaw) {
    for (const idNode of _.castArray(identifierRaw)) {
      const id = idNode["#text"];
      const scheme = idNode.attributes?.["opf:scheme"];
      identifiers.push({ id, scheme });
    }
  }
  let primaryLanguage: string | null = null;
  if (languageRaw) {
    if (Array.isArray(languageRaw)) {
      const primaryNode =
        languageRaw.find(
          (languageNode) => languageNode.attributes?.["opf:primary"] === "true",
        ) || languageRaw[0];
      primaryLanguage = primaryNode["#text"];
    } else {
      primaryLanguage = languageRaw["#text"];
    }
  }

  return { title, creators, dateOfPublication, identifiers, primaryLanguage };
}

function getPrefixedNode(metadata: XmlNode, nodeName: string, prefix: string) {
  return (metadata[`${prefix}:${nodeName}`] || metadata[nodeName]) as
    | XmlNode
    | XmlNode[]
    | undefined;
}

function assertRequiredDcNodes(
  data: { title: string | null; primaryLanguage: string | null },
  filepath: string,
): asserts data is { title: string; primaryLanguage: string } {
  const { title, primaryLanguage } = data;
  const missing = [];
  if (!title) {
    missing.push("title");
  }
  if (!primaryLanguage) {
    missing.push("language");
  }
  if (missing.length > 0) {
    throw new Error(`Missing metadata: ${missing.join(", ")} - ${filepath}`);
  }
}
