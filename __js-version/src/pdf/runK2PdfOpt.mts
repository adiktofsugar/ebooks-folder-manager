import { execSync } from "node:child_process";

export default function runK2PdfOpt(inFilepath: string, outFilepath: string) {
  execSync(
    // -om = output margin
    // -ds = document scale
    // -w = width of reader
    // -h = height of reader
    // -o = output file
    `k2pdfopt -om 0.1 -ds 0.5 -w 1264 -h 1680 -o "${outFilepath}" "${inFilepath}"`,
    // need to ignore stdin so it doesn't go into interactive mode
    { stdio: ["ignore", "ignore", "inherit"] },
  );
}
