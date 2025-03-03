import prompts from "prompts";
import checkCommand from "./utils/checkCommand.mjs";
import { execSync } from "node:child_process";

const instructions = `
To install k2pdfopt, go https://willus.org/k2pdfopt/download
Download the correct one and install globally.
`;

export default async function ensureK2pdfopt() {
  if (!checkCommand("k2pdfopt")) {
    console.log(instructions);
    throw new Error("k2pdfopt is not installed");
  }
}
