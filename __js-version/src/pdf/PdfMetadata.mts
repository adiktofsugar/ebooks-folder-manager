import { fileURLToPath } from "node:url";
import PoetryRunner from "../lib/PoetryRunner.mjs";

const poetryRunner = new PoetryRunner(
  fileURLToPath(new URL("../../pdfmeta", import.meta.url)),
);
export interface PdfMetadataValue {
  /**
   * is this the k2pdfopt version?
   */
  isK2pdfoptVersion: boolean;
}

export default class PdfMetadata {
  filepath;
  constructor(filepath: string) {
    this.filepath = filepath;
  }
  setMetadata(value: Partial<PdfMetadataValue>) {
    poetryRunner.run("pdfmeta", [this.filepath, JSON.stringify(value)]);
  }
  getMetadata(): PdfMetadataValue {
    const val = poetryRunner.run("pdfmeta", [this.filepath]);
    return JSON.parse(val.toString()) as PdfMetadataValue;
  }
}
