import { fileURLToPath } from "node:url";
import PoetryRunner from "../lib/PoetryRunner.mjs";

const poetryRunner = new PoetryRunner(
  fileURLToPath(new URL("../../pdfmeta", import.meta.url)),
);
export interface MetadataValue {
  /**
   * is this the k2pdfopt version?
   */
  isK2pdfoptVersion: boolean;
}

export default class Metadata {
  filepath;
  constructor(filepath: string) {
    this.filepath = filepath;
  }
  async setMetadata(value: Partial<MetadataValue>) {
    poetryRunner.run("pdfmeta", [this.filepath, JSON.stringify(value)]);
  }
  getMetadata(): MetadataValue {
    const val = poetryRunner.run("pdfmeta", [this.filepath]);
    return JSON.parse(val.toString()) as MetadataValue;
  }
}
