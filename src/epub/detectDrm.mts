import { fileURLToPath } from "node:url";
import PoetryRunner from "../lib/PoetryRunner.mjs";

const poetryRunner = new PoetryRunner(
  fileURLToPath(new URL("../../dedrm", import.meta.url)),
);

export default function detectDrm(inFilepath: string) {
  const drmKind = poetryRunner
    .run("epubtest", [inFilepath])
    .toString()
    .trim()
    .toLowerCase();
  if (drmKind === "adobe") {
    return "adobe";
  }
  if (drmKind === "unencrypted") {
    return "unencrypted";
  }
  throw new Error(`Unknown DRM kind: ${drmKind}`);
}
