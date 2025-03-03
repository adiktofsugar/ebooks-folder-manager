import { execSync } from "node:child_process";

/**
 *
 * @param cmd cmd to check (via command -v)
 * @returns The path to the command
 */
export default function checkCommand(cmd: string): string | undefined {
  try {
    return execSync(`command -v ${cmd}`).toString().trim();
  } catch (e) {
    if (isExecError(e)) {
      if (e.status === 1) {
        throw new Error(`Command not found: ${cmd}`);
      }
      return undefined;
    }
    throw e;
  }
}

function isExecError(e: unknown): e is Error & { status: number } {
  return Boolean(e instanceof Error && "status" in e);
}
