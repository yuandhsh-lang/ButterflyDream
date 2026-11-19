import { readFileSync } from "node:fs";
import path from "node:path";
import type { TextTo3dRequest } from "@manycore/aholo-sdk-lux3d";
import {
  createAnimationTask,
  createPartSplitTask,
  createTextTask,
  listTasks,
  retrieveTask,
  uploadOwnedFile,
  waitForTask,
} from "./client.ts";
import { downloadTaskOutputs } from "./download.ts";
import { errorRecord, redact } from "./ledger.ts";
import { taskDirectory, workspacePath } from "./paths.ts";

const args = process.argv.slice(2);
const command = args[0] ?? "help";
const approved = args.includes("--approve-create");
const confirmedOwned = args.includes("--confirm-owned");

function required(index: number, name: string): string {
  const value = args[index];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

function prompt(file: string): string {
  return readFileSync(workspacePath(file), "utf8").trim();
}

async function run(): Promise<unknown> {
  switch (command) {
    case "help":
      return { commands: ["create-text", "create-animation", "split", "upload", "retrieve", "wait", "download", "history"], creationRequires: "--approve-create", uploadRequires: "--confirm-owned", keyEnvironmentVariables: ["AHOLO_API_KEY", "AHOLO_API_KEY_BACKUP"], regionEnvironmentVariable: "AHOLO_REGION=cn|com" };
    case "create-text": {
      const assetId = required(1, "asset ID");
      const request: TextTo3dRequest = { prompt: prompt(required(2, "prompt file")), version: "G1", faceCount: 50000, outputFormat: ["zip", "glb"], enablePbr: true };
      return { taskId: await createTextTask(assetId, request, approved) };
    }
    case "create-animation":
      return { taskId: await createAnimationTask(required(1, "asset ID"), { glbUrl: required(2, "GLB URL"), prompt: prompt(required(3, "prompt file")) }, approved) };
    case "split":
      return { taskId: await createPartSplitTask(required(1, "asset ID"), { glbUrl: required(2, "GLB URL") }, approved) };
    case "upload":
      return uploadOwnedFile(required(1, "asset ID"), workspacePath(required(2, "file")), confirmedOwned);
    case "retrieve":
      return retrieveTask(required(1, "task ID"));
    case "wait":
      return waitForTask(required(1, "task ID"), Number(args[2] ?? 900000));
    case "download": {
      const taskId = required(1, "task ID");
      const task = await retrieveTask(taskId);
      return downloadTaskOutputs(task, taskDirectory(taskId));
    }
    case "history":
      return listTasks();
    default:
      throw new Error(`Unknown command: ${command}`);
  }
}

try {
  const result = await run();
  console.log(JSON.stringify(redact(result), null, 2));
} catch (error) {
  console.error(JSON.stringify({ status: "ERROR", error: errorRecord(error) }, null, 2));
  process.exitCode = 1;
}
