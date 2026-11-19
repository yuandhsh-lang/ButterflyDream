import { createHash } from "node:crypto";
import { createWriteStream, existsSync } from "node:fs";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import type { Lux3dTaskResult, TaskOutput } from "@manycore/aholo-sdk-lux3d";
import { writeJson } from "./ledger.ts";

export type OutputEntry = { index: number; content: string; url?: string };

export function outputEntries(outputs: TaskOutput[] = []): OutputEntry[] {
  const entries: OutputEntry[] = [];
  outputs.forEach((output, index) => {
    const content = output.content?.trim();
    if (!content || content === "NOT_REQUESTED") return;
    if (content.startsWith("[")) {
      try {
        const values = JSON.parse(content);
        if (Array.isArray(values)) {
          values.forEach((value, subIndex) => {
            if (typeof value === "string") entries.push({ index: index * 100 + subIndex, content: value, url: /^https?:\/\//i.test(value) ? value : undefined });
          });
          return;
        }
      } catch {}
    }
    entries.push({ index, content, url: /^https?:\/\//i.test(content) ? content : undefined });
  });
  return entries;
}

export function checkMagicBytes(bytes: Uint8Array, extension: string): void {
  if (extension === ".glb" && String.fromCharCode(...bytes.slice(0, 4)) !== "glTF") throw new Error("Downloaded GLB failed magic validation");
  if (extension === ".zip" && !(bytes[0] === 0x50 && bytes[1] === 0x4b)) throw new Error("Downloaded ZIP failed magic validation");
}

async function hashFile(filePath: string): Promise<string> {
  const bytes = await readFile(filePath);
  return createHash("sha256").update(bytes).digest("hex");
}

function outputName(entry: OutputEntry): string {
  if (!entry.url) return `output-${entry.index}.txt`;
  const url = new URL(entry.url);
  const base = decodeURIComponent(path.basename(url.pathname));
  const safe = base.replace(/[^a-zA-Z0-9._-]/g, "_");
  if (!safe || safe === "." || safe === "..") throw new Error("Output URL has no safe filename");
  return `output-${entry.index}-${safe}`;
}

export async function downloadTaskOutputs(task: Lux3dTaskResult, directory: string): Promise<Record<string, unknown>> {
  if (task.status !== 3) throw new Error(`Task ${task.taskId} is not successful; status=${task.status}`);
  const entries = outputEntries(task.outputs);
  if (!entries.length) throw new Error("Successful task contains no downloadable or textual outputs");
  await mkdir(directory, { recursive: true });
  const results = [];
  for (const entry of entries) {
    const destination = path.join(directory, outputName(entry));
    if (!entry.url) {
      await writeFile(destination, entry.content, "utf8");
      results.push({ index: entry.index, file: path.basename(destination), bytes: Buffer.byteLength(entry.content), sha256: await hashFile(destination), kind: "text" });
      continue;
    }
    let reused = false;
    if (existsSync(destination)) {
      reused = true;
    } else {
      const response = await fetch(entry.url, { signal: AbortSignal.timeout(600000) });
      if (!response.ok) throw new Error(`Output download failed with HTTP ${response.status}`);
      if ((response.headers.get("content-type") ?? "").toLowerCase().includes("text/html")) throw new Error("Output download returned HTML instead of an asset");
      if (!response.body) throw new Error("Output download has no response body");
      const pending = destination + ".part";
      await pipeline(Readable.fromWeb(response.body as never), createWriteStream(pending));
      await rename(pending, destination);
    }
    const bytes = await readFile(destination);
    checkMagicBytes(bytes, path.extname(destination).toLowerCase());
    results.push({ index: entry.index, source: entry.url, file: path.basename(destination), bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex"), reused, kind: "file" });
  }
  const report = { taskId: task.taskId, downloadedAt: new Date().toISOString(), status: "DOWNLOADED", outputs: results };
  await writeJson(path.join(directory, "download-report.json"), report);
  return report;
}
