import os from "node:os";
import parseArgs from "minimist";
import Logger from "./logger.mjs";
import path from "node:path";
import type { Action } from "./interfaces.mjs";
import run from "./index.mjs";
import { fileURLToPath } from "node:url";
import { execSync, spawn } from "node:child_process";
import ensurePoetry from "./env/ensurePoetry.mjs";
import ensureK2pdfopt from "./env/ensureK2pdfopt.mjs";

const usage = `
efm [-h][--dry][--watch][--loglevel=debug|info|error][--adobekey=<adobekey>] <folder> [<action> ...]
-h        help
--dry     print what each action would do without actually doing it
--watch   watch folder for changes
--loglevel  <loglevel> set log level (default: info)
--adobekey  <adobekey> path to Adobe key file for use with dedrm of adobe-DRM'd files

<action>  is one of:
  - drm           remove DRM from files (backs up original as .bak)
  - rename        rename files based on metadata
  - print         print metadata to console
  - print:<file>  print metadata to file
  - pdf           reformat a PDF via k2pdfopt (backs up original as .bak)
  - none          do nothing (useful for testing to see if we don't throw any errors)

Run efm on folder. This will walk that folder recursively and perform all actions you specify.
If no actions are specified, will use any efm.(yaml|yml|json|jsonc) files in the folder.
`;

const args = parseArgs(process.argv.slice(2), {
  boolean: ["h", "dry", "watch"],
  alias: { h: "help" },
});

if (args.help) {
  console.log(usage);
  process.exit(0);
}

const [dirpathRaw, ...actionsRaw] = args._;
if (!dirpathRaw) {
  console.error("No folder specified");
  process.exit(1);
}

Logger.useDefaults();
const loglevel = (args.loglevel || "info").toLowerCase();
switch (loglevel) {
  case "debug":
    Logger.setLevel(Logger.DEBUG);
    break;
  case "info":
    Logger.setLevel(Logger.INFO);
    break;
  case "error":
    Logger.setLevel(Logger.ERROR);
    break;
  default:
    console.error(`Unknown log level: ${loglevel}`);
    process.exit(1);
}

const dirpath = path.resolve(dirpathRaw);

const commandsRequired = new Set<string>();
const actions: Action[] = actionsRaw.map((action) => {
  if (action === "drm") {
    commandsRequired.add("poetry");
    return { type: "drm" };
  }
  if (action === "rename") {
    return { type: "rename" };
  }
  if (action === "print") {
    return { type: "print" };
  }
  if (action.startsWith("print:")) {
    return { type: "print", filename: action.slice(6) };
  }
  if (action === "pdf") {
    commandsRequired.add("k2pdfopt");
    commandsRequired.add("poetry");
    return { type: "pdf" };
  }
  if (action === "none") {
    return { type: "none" };
  }
  throw new Error(`Unknown action: ${action}`);
});
if (actions.length === 0) {
  actions.push({ type: "print" });
}

for (const command of commandsRequired) {
  if (command === "poetry") {
    await ensurePoetry();
  } else if (command === "k2pdfopt") {
    await ensureK2pdfopt();
  } else {
    throw new Error(`Unknown required command: ${command}`);
  }
}

await run(
  dirpath,
  {
    dry: args.dry,
    watch: args.watch,
    adobeKeyFilepath: expandFilepath(args.adobekey),
  },
  actions,
);
if (args.watch) {
  const watchExecFilepath = fileURLToPath(
    new URL("../bin/watchexec", import.meta.url),
  );
  console.log(
    "should run ",
    "bash",

    watchExecFilepath,
    "-r",
    dirpath,
    "--",
    ...process.argv.filter((entry) => entry !== "--watch"),
  );
  spawn(
    "bash",
    [
      watchExecFilepath,
      "-w",
      dirpath,
      "--",
      ...process.argv.filter((entry) => entry !== "--watch"),
    ],
    {
      stdio: "inherit",
    },
  );
}

function expandFilepath(filepath: string | undefined) {
  if (!filepath) {
    return undefined;
  }
  if (filepath.startsWith("~/")) {
    return path.resolve(os.homedir(), filepath.slice(2));
  }
  return path.resolve(filepath);
}
