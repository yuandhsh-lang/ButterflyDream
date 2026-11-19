import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  createLux3dClient,
  type ArticulationAnimationRequest,
  type Lux3dTaskResult,
  type PartSplitRequest,
  type TextTo3dRequest,
} from "@manycore/aholo-sdk-lux3d";
import { createAssetClient } from "@manycore/aholo-sdk-asset";
import { PROJECT_ROOT, taskDirectory } from "./paths.ts";
import { writeJson } from "./ledger.ts";

const localEnv = new URL("../.env.local", import.meta.url);
if (existsSync(localEnv)) process.loadEnvFile(localEnv);

function region(): "cn" | "com" {
  const value = process.env.AHOLO_REGION ?? "cn";
  if (value !== "cn" && value !== "com") throw new Error("AHOLO_REGION must be cn or com");
  return value;
}

function primaryKey(): string | undefined {
  return process.env.AHOLO_API_KEY?.trim() || process.env.AHOLO_API_KEY_BACKUP?.trim();
}

function requireKey(): void {
  if (!primaryKey()) {
    throw new Error("AHOLO_API_KEY or AHOLO_API_KEY_BACKUP is not configured; no official API request was made");
  }
}

function isQuotaError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const candidate = error as { statusCode?: unknown; message?: unknown; bizCode?: unknown; body?: unknown };
  if (candidate.statusCode === 402) return true;
  let bodyText = "";
  try {
    bodyText = JSON.stringify(candidate.body) ?? "";
  } catch {}
  const text = [candidate.message, candidate.bizCode, bodyText]
    .filter((value): value is string => typeof value === "string")
    .join(" ")
    .toLowerCase();
  if (/rate.?limit|too many requests|请求频繁/.test(text)) return false;
  return /insufficient|quota|balance|credit|积分|额度|余额|配额/.test(text);
}

export async function withKeyFallback<T>(operation: (apiKey: string) => Promise<T>): Promise<T> {
  const primary = process.env.AHOLO_API_KEY?.trim();
  const backup = process.env.AHOLO_API_KEY_BACKUP?.trim();
  const first = primary || backup;
  if (!first) {
    requireKey();
    throw new Error("No Aholo API key is configured");
  }
  try {
    return await operation(first);
  } catch (error) {
    if (!backup || backup === first || !isQuotaError(error)) throw error;
    return operation(backup);
  }
}

function lux3dClient(apiKey?: string) {
  requireKey();
  return createLux3dClient({ region: region(), apiKey: apiKey ?? primaryKey() });
}

function requireCreateApproval(approved: boolean): void {
  if (!approved) {
    throw new Error("Creation blocked: provide --approve-create only after cost and quota are confirmed");
  }
}

function recordPath(taskId: number | string): string {
  return path.join(taskDirectory(taskId), "task-record.json");
}

function saveTask(taskId: number | string, value: Record<string, unknown>): void {
  const file = recordPath(taskId);
  const previous = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};
  writeJson(file, {
    ...previous,
    ...value,
    taskId: String(taskId),
    updatedAt: new Date().toISOString(),
    apiRegion: region(),
  });
}

function requestHash(request: unknown): string {
  return createHash("sha256").update(JSON.stringify(request)).digest("hex");
}

function validateTaskId(value: number): number {
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error("Official SDK returned an invalid task ID");
  return value;
}

export async function createTextTask(assetId: string, request: TextTo3dRequest, approved: boolean): Promise<number> {
  requireCreateApproval(approved);
  requireKey();
  const taskId = validateTaskId(await withKeyFallback((apiKey) => lux3dClient(apiKey).textTo3d.create(request)));
  saveTask(taskId, { assetId, operation: "textTo3d.create", request, requestHash: requestHash(request), status: "CREATED", createdAt: new Date().toISOString() });
  return taskId;
}

export async function createAnimationTask(assetId: string, request: ArticulationAnimationRequest, approved: boolean): Promise<number> {
  requireCreateApproval(approved);
  requireKey();
  const taskId = validateTaskId(await withKeyFallback((apiKey) => lux3dClient(apiKey).articulationAnimation.create(request)));
  saveTask(taskId, { assetId, operation: "articulationAnimation.create", request, requestHash: requestHash(request), status: "CREATED", createdAt: new Date().toISOString() });
  return taskId;
}

export async function createPartSplitTask(assetId: string, request: PartSplitRequest, approved: boolean): Promise<number> {
  requireCreateApproval(approved);
  requireKey();
  const taskId = validateTaskId(await withKeyFallback((apiKey) => lux3dClient(apiKey).partSplit.create(request)));
  saveTask(taskId, { assetId, operation: "partSplit.create", request, requestHash: requestHash(request), status: "CREATED", createdAt: new Date().toISOString() });
  return taskId;
}

export async function retrieveTask(taskId: number | string): Promise<Lux3dTaskResult> {
  requireKey();
  const result = await lux3dClient().tasks.retrieve(taskId);
  saveTask(taskId, { status: result.status, outputs: result.outputs, bizId: result.bizId });
  return result;
}

export async function waitForTask(taskId: number | string, timeoutMs = 15 * 60 * 1000): Promise<Lux3dTaskResult> {
  requireKey();
  const result = await lux3dClient().tasks.waitFor(taskId, { intervalMs: 15000, timeoutMs });
  saveTask(taskId, { status: result.status, outputs: result.outputs, bizId: result.bizId });
  return result;
}

export async function listTasks(page = 1, pageSize = 20) {
  requireKey();
  return lux3dClient().tasks.list({ page, pageSize });
}

export async function uploadOwnedFile(assetId: string, filePath: string, confirmedOwned: boolean) {
  if (!confirmedOwned) throw new Error("Upload blocked: provide --confirm-owned only for original or generated assets");
  requireKey();
  const resolved = path.resolve(filePath);
  const allowed = path.join(PROJECT_ROOT, "LuxAssets");
  if (resolved !== allowed && !resolved.startsWith(allowed + path.sep)) {
    throw new Error("Upload is restricted to files inside LuxAssets; third-party scenes must not be uploaded");
  }
  if (!existsSync(resolved)) throw new Error("Upload file does not exist");
  const result = await createAssetClient({ region: region(), apiKey: primaryKey() }).uploadFile(resolved, { filename: path.basename(resolved) });
  writeJson(path.join(PROJECT_ROOT, "LuxAssets", "Raw", "uploads", `${assetId}.json`), {
    assetId,
    file: path.relative(PROJECT_ROOT, resolved),
    uploadedAt: new Date().toISOString(),
    result,
  });
  return result;
}
