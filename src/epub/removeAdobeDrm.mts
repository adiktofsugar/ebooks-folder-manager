import { fileURLToPath } from "node:url";
import PoetryRunner from "../lib/PoetryRunner.mjs";

const poetryRunner = new PoetryRunner(
  fileURLToPath(new URL("../../dedrm", import.meta.url)),
);

export default function removeAdobeDrm(
  inFilepath: string,
  outFilepath: string,
  keyFilepath: string,
) {
  poetryRunner.run("epubdecrypt", [keyFilepath, inFilepath, outFilepath]);
}
