import { fileURLToPath } from "node:url";
import path from "node:path";

export const PROJECT_ROOT = fileURLToPath(new URL("../../..", import.meta.url));
export const LUX_RAW_ROOT = path.join(PROJECT_ROOT, "LuxAssets", "Raw");

export function workspacePath(relative: string): string {
  const resolved = path.resolve(PROJECT_ROOT, relative);
  const root = path.resolve(PROJECT_ROOT);
  if (resolved !== root && !resolved.startsWith(root + path.sep)) {
    throw new Error("Path must remain inside the project workspace");
  }
  return resolved;
}

export function taskDirectory(taskId: number | string): string {
  const value = String(taskId);
  if (!/^[a-zA-Z0-9_-]+$/.test(value)) throw new Error("Invalid task ID");
  return path.join(LUX_RAW_ROOT, value);
}
