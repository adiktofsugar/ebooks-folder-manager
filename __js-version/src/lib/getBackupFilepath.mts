import fs from "node:fs";
export default function getBackupFilepath(filepath: string) {
  let backupFilepath = `${filepath}.bak`;
  let i = 0;
  while (fs.existsSync(backupFilepath)) {
    i += 1;
    backupFilepath = `${filepath}.${i}.bak`;
  }
  return backupFilepath;
}
