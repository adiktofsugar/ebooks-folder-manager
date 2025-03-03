import spawnSyncError from "./spawnSyncError.mjs";

export default class PoetryRunner {
  private projectDirpath: string;
  private hasRunInstall = false;
  constructor(projectDirpath: string) {
    this.projectDirpath = projectDirpath;
  }

  run(scriptName: string, args: string[]) {
    if (!this.hasRunInstall) {
      spawnSyncError("poetry", ["-P", this.projectDirpath, "install"]);
      this.hasRunInstall = true;
    }
    return spawnSyncError("poetry", [
      "-P",
      this.projectDirpath,
      "run",
      scriptName,
      ...args,
    ]);
  }
}
