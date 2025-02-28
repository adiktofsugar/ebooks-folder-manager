import parseArgs from "minimist";
import Logger from "./logger.mjs";
import path from "node:path";
import type { Action } from "./interfaces.mjs";
import run from "./index.mjs";

const usage = `
efm [-h][--dry][--watch][--loglevel=debug|info|error] <folder> [<action> ...]
-h        help
--dry     print what each action would do without actually doing it
--watch   watch folder for changes
--loglevel  set log level (default: info)

<action>  is one of:
  - drm           remove DRM from files
  - rename        rename files based on metadata
  - print         print metadata to console (can't be combined with --watch)
  - print:<file>  print metadata to file

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
const loglevel = args.loglevel || "info";
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
const actions: Action[] = actionsRaw.map((action) => {
  if (action === "drm") {
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
  throw new Error(`Unknown action: ${action}`);
});

await run(dirpath, { dry: args.dry, watch: args.watch }, actions);
