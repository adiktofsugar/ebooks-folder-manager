import getEpubMetadata from "../epub/getMetadata.mjs";

export default async function getMetadata(filepath: string) {
  // pymupdf has support for epub, mobi, and pdf, so I should probably move this
  //   logic over there
  if (filepath.endsWith(".epub")) {
    return getEpubMetadata(filepath);
  }
  return null;
}
