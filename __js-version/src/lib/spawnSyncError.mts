import { spawnSync } from "node:child_process";

export default function spawnSyncError(
  cmd: string,
  args: string[],
  options?: { cwd?: string; stdin?: "inherit" | "ignore" },
) {
  const result = spawnSync(cmd, args, options);
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(
      `Command failed: ${cmd} ${args.join(" ")}\n${result.stderr.toString()}`,
    );
  }
  return result.stdout;
}
