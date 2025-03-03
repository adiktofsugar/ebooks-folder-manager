import prompts from "prompts";
import checkCommand from "./utils/checkCommand.mjs";
import { execSync } from "node:child_process";

export default async function ensurePoetry() {
  if (!checkCommand("poetry")) {
    console.log("Poetry is not installed");
    const { shouldInstallPoetry } = await prompts({
      type: "confirm",
      name: "shouldInstallPoetry",
      message:
        '"poetry" is required. Do you want to install Poetry from the official script?',
      initial: true,
    });
    if (shouldInstallPoetry) {
      console.log("Installing Poetry...");
      execSync(`${new URL("../../bin/install-poetry", import.meta.url)}`, {
        stdio: "inherit",
      });
    }
  }
}
